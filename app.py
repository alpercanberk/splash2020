from flask import Flask, redirect, render_template, request, jsonify, url_for, Response
import flask
import flask_excel as excel

import datetime
import json
import os

import random

import time
import atexit

from routes import *
from utils import *
from lists import *

from firebase_admin import credentials, firestore, initialize_app

app = Flask(__name__)
#register blueprints for routes
app.register_blueprint(routes)
#initialize the excel module
excel.init_excel(app)
#setup the database
#setup secret key for oauth2
app.secret_key = os.environ['SECRET_KEY']

cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()


users_ref = db.collection('users')
pause_ref = db.collection('pause')
matches_ref = db.collection('matches')
immunity_ref = db.collection('immunity')
codes_ref = db.collection('codes')
stats_ref = db.collection('stats')

from firestore_models import *

def expire_ability(code, used_by, used_on):
    ability = codes_ref.where("code","==",code).get()

    if(len(ability) > 0):
        ability = ability[0].to_dict()
        ability["used_at"] = time_now()
        ability["used_on"] = used_on
        ability["used_by"] = used_by

        user = users_ref.where("email","==",used_by).get()
        if(len(user) > 0):
            user = user[0].to_dict()
            user["codes_found"] += 1

        users_ref.document(user["user_id"]).update(user)
        codes_ref.document(ability["code"]).update(ability)
    else:
        print("Something went wrong...")

def create_new_user(name, email):
    print("User creation initialized")

    stats = stats_ref.document("0").get().to_dict()
    stats["n_users_alive"] += 1
    stats_ref.document("0").update(stats)

    id = generate_user_id()
    new_user = user_model(name, email, id)
    users_ref.document(id).set(new_user)

    return "User created"


def create_new_code(code, duration):
    print("Code creation initialized")
    # try:
    id = code
    new_code = code_model(code, duration)
    codes_ref.document(id).set(new_code)

    return "Code created"
    # except Exception as e:
    #     return str(e)


def create_new_match(hunter_email, target_email):
    id = generate_random_id()
    stats = stats_ref.document("0").get().to_dict()
    stats["n_matches_ongoing"] += 1
    stats_ref.document("0").update(stats)
    try:
        new_match = match_model(hunter_email, target_email, id)
        matches_ref.document(id).set(new_match)
        # print("Match created!")
    except Exception as e:
        # print("Match creation failed")
        print(str(e))

def get_table(table):
    return [doc.to_dict() for doc in table.stream()]

def get_basic_stats():

    stats = stats_ref.document("0").get().to_dict()
    n_users = stats["n_users"]
    n_matches = stats["n_matches"]
    n_users_alive = stats["n_users_alive"]
    n_matches_ongoing = stats["n_matches_ongoing"]

    return n_users, n_matches, n_users_alive, n_matches_ongoing

def get_leaderboard(n_users):
    leaderboard = users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).limit(n_users).get()
    return [user.dict() for user in leaderboard]

def compute_ranks():

    all_users = [user.to_dict() for user in users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).get()]
    for i in range(0, len(all_users)):
        all_users[i]["rank"] = i
        users_ref.document(all_users[i]["user_id"]).update(all_users[i])

def eliminate_user(email, increment_elimination_count=False):

    print("Eliminate user function activated")

    user_being_eliminated = users_ref.where("email","==",email).where("time_eliminated", "==", "").get()

    #check if the user exists
    if(len(user_being_eliminated) > 0):
        user_being_eliminated = user_being_eliminated[0].to_dict()
        print(user_being_eliminated)

        # print(">>>")
        # print(matches_ref.where("hunter_email","==",email).where("time_ended","==","").get())
        # print(matches_ref.where("hunter_email","==",email).get())
        # print(">>>")


        user_active_match_hunter = matches_ref.where("hunter_email","==",email).where("time_ended","==","").get()[0].to_dict()
        target_of_user_email = user_active_match_hunter["target_email"]
        target_of_user = users_ref.where("email","==",target_of_user_email).get()[0].to_dict()

        user_active_match_target = matches_ref.where("target_email","==",email).where("time_ended","==","").get()[0].to_dict()

        hunter_of_user_email = user_active_match_target["hunter_email"]
        hunter_of_user = users_ref.where("email","==",hunter_of_user_email).get()[0].to_dict()

        print(">>>>>>")
        print("target of user", target_of_user)
        print("hunter of user", hunter_of_user)
        print(">>>>>>")

        #increment elimination count of the hunter of this user if needed
        if increment_elimination_count:
            hunter_of_user["number_of_elims"] += 1
            hunter_of_user["time_of_last_elim"] = time_now()
            users_ref.document(hunter_of_user["user_id"]).update(hunter_of_user)
            print("Incremented elimination count")
        else:
            print("Didn't increment elimination count")

        if increment_elimination_count:
            reas = "Elimination"
        else:
            reas = "DQ"

        # #complete both hunter and target elims with the given reason
        terminate_match(user_active_match_hunter, "Hunter died")
        terminate_match(user_active_match_target, reas)

        create_new_match(hunter_of_user_email, target_of_user_email)
        print("New match created!")

        # #kill the usermatch["time_ended"] = time_now()
        user_being_eliminated["time_eliminated"]=time_now()
        users_ref.document(user_being_eliminated["user_id"]).update(user_being_eliminated)

        stats = stats_ref.document("0").get().to_dict()
        stats["n_users_alive"] -= 1
        stats_ref.document("0").update(stats)
        #
        compute_ranks()

        return "Elimination successful"
    else:
        return "User not found."

def terminate_match(match, reason):
    match["time_ended"] = time_now()
    match["reason"] = reason
    matches_ref.document(match["id"]).update(match)
    stats = stats_ref.document("0").get().to_dict()
    stats["n_matches_ongoing"] -= 1
    stats_ref.document("0").update(stats)
    return "ok"

def is_admin():
    if(flask.session["user_info"]["email"] in admins):
        return True
    return False

def is_logged_in():
    if("user_info" in flask.session.keys()):
        user_found = users_ref.where("email","==",flask.session["user_info"]["email"]).get()
        if len(user_found) > 0:
            return True
        return False
    return False


def is_paused():
    is_paused = pause_ref.document("0").get().to_dict()["is_paused"]
    return is_paused

def is_immunity_on():
    is_immunity_on = immunity_ref.document("0").get().to_dict()["is_immunity_on"]
    return is_immunity_on

def set_all_stats():
    n_users, n_matches, n_users_alive, n_matches_ongoing = get_basic_stats()

    leaderboard = get_leaderboard(10)

    number_of_codes_in_game = len(codes_ref.get())
    number_of_codes_activated = len(codes_ref.where("used_at","==","").get())

    code_leaderboard = [user.to_dict() for user in users_ref.order_by("codes_found", direction=firestore.Query.DESCENDING).limit(3).get()]

    # qualified_board = [user.serialize() for user in User.query.filter("-Q*" in User.name).all()]

    immunity_board = [user.to_dict() for user in users_ref.where("immunity_duration","!=", 0).get()]

    fmt = "%Y-%m-%d %H:%M:%S"

    recent_elims = 0
    for user in users_ref.stream():
        if(within_24_hours(user.to_dict()["time_eliminated"], datetime.now().strftime(fmt))):
            recent_elims += 1

    print(">>>>>>")
    print(recent_elims)
    print(">>>>>>")

    stats = stats_ref.document("0").get().to_dict()
    stats["all_stats"] = str({
        "n_users":n_users,
        "n_matches":n_matches,
        "n_users_alive":n_users_alive,
        "n_matches_ongoing":n_matches_ongoing,
        "leaderboard":leaderboard,
        "number_of_codes_in_game":number_of_codes_in_game,
        "number_of_codes_activated":number_of_codes_activated,
        "code_leaderboard":code_leaderboard,
        # "qualified_board":qualified_board,
        "immunity_board":immunity_board,
        "is_paused": (is_paused()),
        "is_immunity_on":(is_immunity_on()),
        "recent_elims":recent_elims
        })
    stats_ref.document("0").update(stats)

def get_all_stats():
    # print("receiving all stats")
    # print(stats_ref.document("0").get().to_dict()["all_stats"])
    return eval(stats_ref.document("0").get().to_dict()["all_stats"])

def grant_immunity(email, minutes):
    user_found = users_ref.where("email","==",email).where("time_eliminated","==","").get()
    if len(user_found) > 0:
        user_found = user_found[0].to_dict()
        user_found["immunity_duration"] += int(minutes)
        users_ref.document(user_found["user_id"]).update(user_found)
        return True
    else:
        return False

def insert_into_chain(email, reason):

    #find all matches that are currently active
    all_matches = [match.to_dict() for match in matches_ref.where("time_ended","==","").get()]
    print("all matches", all_matches)

    print("Len all matches", len(all_matches))
    random_index = random.randint(0, len(all_matches)-1)
    print("random index", random_index)
    match_picked_id = all_matches[random_index]["id"]
    match_picked = matches_ref.where("id", "==", match_picked_id).get()[0].to_dict()

    match_hunter_email = match_picked["hunter_email"]
    match_target_email = match_picked["target_email"]

    # #complete elim_picked
    terminate_match(match_picked, reason)

    create_new_match(match_hunter_email, email)
    create_new_match(email, match_target_email)

def revive_user(email):
    user_found = users_ref.where("email","==", email).get()
    if len(user_found) > 0:
        user_found = user_found[0].to_dict()
        if(user_found["time_eliminated"] == ""):
            return False
        user_found["time_eliminated"] = ""
        user_found["num_revives"] += 1
        users_ref.document(user_found["user_id"]).update(user_found)
        insert_into_chain(user_found["email"], "Revive")
        return True
    else:
        return False

@app.route('/eliminate_user_admin', methods=["POST"])
def eliminate_user_admin_route():
    if(is_admin()):
        print("Eliminating a user...")
        data = request.json
        return eliminate_user(data["email"], data["increment_elimination_count"])
    else:
        return "Damn you're smart, come to programming club."

@app.route('/eliminate_user', methods=["POST"])
def eliminate_user_route():
    #if someone tries to fuck up the program, their identity will be known
    print(flask.session["user_info"]["email"], "attempting to eliminate a user")
    code = request.json["code"]

    current_match = matches_ref.where("hunter_email","==",flask.session["user_info"]["email"]).where("time_ended","==","")

    if current_match is not None:
        current_target_email = current_match.get()[0].to_dict()["target_email"]
        current_target = users_ref.where("email","==",current_target_email).get()[0].to_dict()
        current_target_id = current_target["user_id"]
        current_target_immunity_duration = current_target["immunity_duration"]
        if not is_paused():
            if(code == current_target_id):
                if(current_target_immunity_duration <= 0 or (not is_immunity_on())):
                    eliminate_user(current_target_email, True)
                    return "Success!"
                else:
                    return "The code is correct, but your target seems to have immunity on."

            else:
                return "Invalid code, try again. (ps. There are 2 trillion possible combinations)"
        else:
            return "Chill out, the game is paused"
    else:
        return "Oops, something went wrong. Contact the admins about this. (Error 186)"

@app.route('/grant_immunity', methods=["POST"])
def grant_immunity_endpoint():
    if is_admin():
        if(grant_immunity(request.json["email"], request.json["duration"])):
            return "Success"
        else:
            return "Oops, something went wrong. Probably entered invalid email"
    else:
        return "No access."

@app.route('/')
def index():
    is_eliminated = False
    if "user_info" in flask.session.keys():
        if(is_admin()):
            all_users = get_table(users_ref)
            all_matches = get_table(matches_ref)
            return render_template('admin.html',
            user_info = flask.session["user_info"],
            logged_in = True,
            user_table = all_users,
            match_table = all_matches,
            basic_stats = (get_basic_stats()),
            is_paused = (is_paused()),
            is_immunity_on=(is_immunity_on()),
            codes_table = (get_table(codes_ref)),
            all_stats = (get_all_stats()),
            )
        else:
            user_found =  users_ref.where('email', '==', flask.session["user_info"]["email"]).get()
            if len(user_found):
                user_found = user_found[0].to_dict()
                print("user is not none >>>", user_found)
                if(not user_found["time_eliminated"] == ""):
                    is_eliminated = True
                    target_info = ""
                if(not is_eliminated):
                    current_match_of_user = matches_ref.where('hunter_email', '==', flask.session["user_info"]["email"]).where("time_ended","==","").get()[0].to_dict()
                    target_info = users_ref.where("email", "==", current_match_of_user["target_email"]).get()[0].to_dict()
                return render_template('home.html',
                    user_info=user_found,
                    target_info=target_info,
                    basic_stats = (get_basic_stats()),
                    logged_in=True,
                    is_paused=(is_paused()),
                    is_immunity_on=(is_immunity_on()),
                    all_stats = (get_all_stats()),
                    is_eliminated = ( not user_found["time_eliminated"] == "")
                    )
            else:
                return render_template('not_logged.html',
                    basic_stats = (get_basic_stats()),
                    all_stats = (get_all_stats()),
                    logged_in=True)
    else:
        return render_template('index.html',
            all_stats = (get_all_stats()),
            logged_in=False)

@app.route('/edit_user', methods=['POST'])
def edit_user():
    print("Edit endpoint activated")
    if(is_admin()):
        print("Editing user...")
        data = request.json

        previous_email = data["previous_email"]
        previous_name = data["previous_name"]
        new_email = data["new_email"]
        new_name = data["new_name"]

        #change the name in matches as well
        user_found = users_ref.where("name","==","previous_name").where("email","==",previous_email).get()

        if len(user_found) > 0:
            user_found = user_found[0].to_dict()

            #change the name in hunter matches
            matches_found_as_hunter = matches_ref.where("hunter_email","==", user_found["email"]).get()
            matches_found_as_target = matches_ref.where("target_email","==",user_found["email"]).get()

            for match in matches_found_as_hunter:
                match["hunter_email"] = new_email
                matches_ref.document(match["id"]).update(match)

            for match in matches_found_as_target:
                match["target_email"] = new_email
                matches_ref.document(match["id"]).update(match)


            user_found["email"] = new_email
            user_found["name"] = new_name
            users_ref.document(user_found["user_id"]).update(user_found)

            print("User edit successful")
            return "User edit successful"
        else:
            print("User not found")
            return "User not found"
    else:
        return "Access denied"

@app.route('/ability/<code>')
def ability(code):
    if "user_info" in flask.session.keys():
        code = codes_ref.where("code","==",code).where("used_at","==","").get()
        if(len(code) > 0):
            code = code[0].to_dict()
            code_found = code["code"]
            print('Someone found a code!')
            if(code_found[0] == "R"):
                return render_template("revive_ability.html", logged_in = True)
            if(code_found[0] == "I"):
                return render_template("immunity_ability.html", logged_in = True, duration=code["duration"])
            if(code_found[0] == "Q"):
                return render_template("qualify_ability.html", logged_in = True)
        else:
            print('Invalid ability code attempt by', flask.session["user_info"]["email"])
            return render_template("invalid_ability_code.html")
    else:
        #TODO make this page
        return "Log in in order to gain new ability by clicking <a href='/auth/google'>here</a>"

@app.route('/ability/')
def ability_index():
    return render_template("invalid_ability_code.html")

@app.route('/pause_game', methods=['POST'])
def pause_game():
    if is_admin():
        pause = pause_ref.document("0").get().to_dict()
        pause["is_paused"] = not pause["is_paused"]
        pause_ref.document("0").update(pause)
        if pause["is_paused"]:
            return "Game paused"
        else:
            return "Game started"
    else:
        return "Access denied"


@app.route('/pause_immunity', methods=['POST'])
def pause_immunity():
    if is_admin():
        immunity = immunity_ref.document("0").get().to_dict()
        immunity["is_immunity_on"] = not immunity["is_immunity_on"]
        immunity_ref.document("0").update(immunity)
        if immunity["is_immunity_on"]:
            return "Immunity started"
        else:
            return "Immunity paused"
    else:
        return "Access denied"

@app.route('/revive_user', methods=['POST'])
def revive_user_endpoint():
    if is_admin():
        if(revive_user(request.json["email"])):
            return "Revive successful"
        else:
            return "Oops, something went wrong. Probably invalid input."
    else:
        return "Access denied"

def parse_code(link):
    return os.path.basename(os.path.dirname(request.json["link"] + "/"))

@app.route('/revive_ability', methods=['POST'])
def revive_ability():
    code_from_link = parse_code(request.json["link"])
    if(is_logged_in() and (len(codes_ref.where("code","==",code_from_link).where("used_at", "==", "").get()) > 0)):
        if(revive_user(request.json["email"])):
            expire_ability(code=code_from_link, used_on=request.json["email"], used_by=flask.session["user_info"]["email"])
            return "Revive successful"
        else:
            return "Invalid attempt. The person you are trying to revive might still be alive or you might have made a spelling error"
    else:
        return "Access denied, try logging in."


@app.route('/qualify_ability', methods=['POST'])
def qualify_user():
    code_from_link = parse_code(request.json["link"])
    #check if the code exists and that it's valid
    if(is_logged_in() and len(codes_ref.where("code","==",code_from_link).where("used_at","==", "").get()) > 0):
        print("Someone is qualifying for the final...")
        user_found = users_ref.where("email","==",flask.session["user_info"]["email"]).get()[0].to_dict()
        eliminate_user(flask.session["user_info"]["email"])
        user_found["name"] = user_found["name"] + " -Q*"
        expire_ability(code=code_from_link, used_by=flask.session["user_info"]["email"], used_on=flask.session["user_info"]["email"])
        users_ref.document(user_found["user_id"]).update(user_found)
        return "Qualified!"
    else:
        return "Access denied, try logging in."

@app.route('/immunity_ability', methods=['POST'])
def immunity_ability():
    code_from_link = parse_code(request.json["link"])
    code = codes_ref.where("code","==",code_from_link).where("used_at","==","").get()
    #check if the code exists and that it's valid
    if(is_logged_in() and (len(code) > 0)):
        code = code[0].to_dict()
        if(is_immunity_on()):
            if(grant_immunity(request.json["email"], code["duration"])):
                print("Someone is activating their immunity ability")
                expire_ability(code=code_from_link, used_by=flask.session["user_info"]["email"], used_on=request.json["email"])
                return "Immunity granted!"
            else:
                return "Oops, something went wrong. Check the validity of your input."
        else:
            return "Sorry, immunity abilities are currently deactivated. You would not want to use your code right now."
    else:
        return "Access denied, try logging in."

# @app.route('/displace_ability', methods = ['POST'])

@app.route('/shuffle_game', methods=['POST'])
def shuffle_game():
    if is_admin():

        for match in matches_ref.stream():
            terminate_match(match.to_dict(), "Game shuffled")

        #finds all alive users and shuffles their emails
        all_users_alive = users_ref.where("time_eliminated", "==", "").get()

        all_emails = []
        for user in all_users_alive:
            all_emails.append(user.to_dict()["email"])
        random.shuffle(all_emails)


        def generate():
            for x in range(0,len(all_emails)-1):
                yield "<div></div> {} out of {} matches created".format(x+1, len(all_emails)-1)
                create_new_match(all_emails[x], all_emails[x+1])
            create_new_match(all_emails[len(all_emails)-1], all_emails[0])
            yield "<div></div> All matches uploaded, let the games begin!"
            yield "<div><button><a href="+ "/" + ">Take me back to admin page</a></button></div>"

        return Response(generate(), mimetype='text/html')

        return "Game shuffled!"
    else:
        return "Access denied"


@app.route('/add_user', methods=['POST'])
def add_user():
    if(is_admin()):

        data = request.json
        email = data["email"]
        name = data["name"]

        #create a new user
        create_new_user(name, email)
        print("New user created!")

        insert_into_chain(email=email, reason="Added user")

        return "New user created!"
    else:
        return "Access denied"


def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


@app.route('/upload', methods=['POST'])
def upload():
    if(is_admin()):
        if request.method == 'POST':
            print(">>>>>>>>>")
            print("Upload activated")
            print(">>>>>>>>>")

            #clears the database
            # User.query.delete()
            delete_collection(users_ref, 50)
            delete_collection(matches_ref, 50)
            delete_collection(codes_ref, 50)
            delete_collection(pause_ref, 1)
            delete_collection(immunity_ref, 1)
            delete_collection(stats_ref, 1)

            #create new pause variable
            pause_ref.document("0").set(pause_model())
            immunity_ref.document("0").set(immunity_model())

            #gets the excel file from front-end
            arr = request.get_array(field_name='file')
            users=[]
            for u in arr:
                users.append({'name':u[0], 'email':u[1]})

            #shuffle the list of users
            random.shuffle(users)

            stats_ref.document("0").set(stats_model(len(users), len(users)))



            create_new_code("I1234", 10)
            create_new_code("R1234", 10)
            create_new_code("Q1234", 10)

            # the generator gives realtime feedback on the users uploaded
            # it also contains the logic for initiating the game
            def generate():
                for x in range(0,len(users)-1):
                    yield "<div></div>"+ str(x+1) +" out of "+ str(len(users)) + " users uploaded."
                    create_new_user(users[x]['name'], users[x]['email'])
                    create_new_match(users[x]['email'], users[x+1]['email'])
                create_new_user(users[len(users)-1]['name'], users[len(users)-1]['email'])
                create_new_match(users[len(users)-1]['email'], users[0]['email'])
                compute_ranks()
                yield "<div></div> All users uploaded, let the games begin!"
                yield "<div><button><a href="+ "/" + ">Take me back to admin page</a></button></div>"
            set_all_stats()
            return Response(generate(), mimetype='text/html')
    return redirect(url_for('index'))

@app.route('/activate_24_hour_round', methods=['POST'])
def activate24():
    if is_admin():

        for match in matches_ref.stream():
            match_dict = match.to_dict()
            if match_dict["time_ended"] == "":
                terminate_match(match_dict, reason="24-R")

        alive_count = 0
        dead_count = 0
        for user in users_ref.stream():
            user = user.to_dict()
            if(not within_24_hours(time_now(), user["time_of_last_elim"])):
                eliminate_user(user["email"])
                dead_count +=1

            else:
                alive_count += 1

        all_users_alive = users_ref.where("time_eliminated", "==", "").get()

        all_emails = []
        for user in all_users_alive:
            all_emails.append(user.to_dict()["email"])
        random.shuffle(all_emails)

        def generate():
            yield "<div>{} users eliminated as a result of the 24-hour round</div>".format(dead_count)
            for x in range(0,len(all_emails)-1):
                yield "<div></div> {} out of {} matches created".format(x+1, len(all_emails)-1)
                create_new_match(all_emails[x], all_emails[x+1])
            create_new_match(all_emails[len(all_emails)-1], all_emails[0])
            yield "<div></div> 24-hour eliminations made!"
            yield "<div><button><a href="+ "/" + ">Take me back to admin page</a></button></div>"

        return Response(generate(), mimetype='text/html')

        return "24 HOUR ROUND ACTIVATED!!!"
    else:
        return "Access denied"

@app.route('/leaderboard')
def leaderboard():
    return str(get_leaderboard(3))

@app.route('/all_stats')
def all_stats():
    return str(get_all_stats())

@app.route('/statistics')
def statistics():
    return render_template("stats.html",logged_in=is_logged_in(), stats=get_all_stats())

@app.route('/team')
def team():
    return render_template("team.html", logged_in = is_logged_in(), team=Lists.team)

@app.route('/hof')
def hof():
    return render_template("hof.html", logged_in = is_logged_in())

@app.route('/announcements')
def announcements():
    return render_template("announcements.html", logged_in=is_logged_in(), announcements=Lists.announcements)

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
