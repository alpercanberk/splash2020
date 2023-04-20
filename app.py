from flask import Flask, redirect, render_template, request, jsonify, url_for, Response
import flask
import flask_excel as excel

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import datetime
import json
import os

import random

import time
import atexit

from routes import *
from utils import *
from lists import *
from flask_mail import Mail, Message

from firebase_admin import credentials, firestore, initialize_app
# from flask_mail import Mail, Message

app = Flask(__name__)
#register blueprints for routes
app.register_blueprint(routes)
#conig email
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'reshwap2019@gmail.com'
app.config['MAIL_PASSWORD'] = 'cyrmevswjqcbqojn'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
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
issues_ref = db.collection('issues')

from firestore_models import *

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "10 per hour"]
)

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

def create_new_issue(user_email, content):
    print("new issue registered")

    id = generate_random_id()
    new_issue = issue_model(user_email, content, id)
    issues_ref.document(id).set(new_issue)

    return "Issue created"

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


def get_basic_stats_admin():
    stats = stats_ref.document("0").get().to_dict()
    n_users = stats["n_users"]
    n_matches = stats["n_matches"]
    n_users_alive = len(users_ref.where("time_eliminated","==","").get())
    n_matches_ongoing = len(matches_ref.where("time_ended","==","").get())

    return n_users, n_matches, n_users_alive, n_matches_ongoing

#changed from "dict()" to "to_dict()"

def get_leaderboard(n_users):
    leaderboard = users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).limit(n_users).get()
    return [user.to_dict() for user in leaderboard]

def eliminate_user(email, increment_elimination_count=False):

    print("Eliminate user function activated")
    print(email)
    user_being_eliminated = users_ref.where("email","==",email).where("time_eliminated", "==", "").get()
    print(user_being_eliminated)
    #check if the user exists
    if(len(user_being_eliminated) > 0):
        user_being_eliminated = user_being_eliminated[0].to_dict()
        print(user_being_eliminated)

        # print(">>>")
        # print(matches_ref.where("hunter_email","==",email).where("time_ended","==","").get())
        # print(matches_ref.where("hunter_email","==",email).get())
        # print(">>>")
        print(">> Debug >>")

        print(matches_ref.where("hunter_email","==",email).get())
        print(matches_ref.where("time_ended","==","").get())
        print(matches_ref.where("hunter_email","==",email).where("time_ended","==","").get())
        print(email)
        print(">>>>")

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

def is_timer_on():
    is_on = pause_ref.document("1").get().to_dict()["is_on"]
    return is_on

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

        stats = stats_ref.document("0").get().to_dict()
        stats["n_users_alive"] += 1
        stats_ref.document("0").update(stats)

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
    code = str.upper(request.json["code"])

    current_match = matches_ref.where("time_ended","==","").where("hunter_email","==",flask.session["user_info"]["email"])

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

        end_day = "0"
        end_hr = "0"
        end_min = "0"
        end_sec = "0"

        if is_timer_on():
            timer = pause_ref.document("1").get().to_dict()
            end_day = timer["end_day"]
            end_hr = timer["end_hr"]
            end_min = timer["end_min"]
            end_sec = timer["end_sec"]

        if(is_admin()):
            all_users = get_table(users_ref)
            all_matches = get_table(matches_ref)
            all_issues = get_table(issues_ref)
            
            return render_template('admin.html',
            user_info = flask.session["user_info"],
            logged_in = True,
            user_table = all_users,
            match_table = all_matches,
            issue_table = all_issues,
            basic_stats = (get_basic_stats_admin()),
            is_paused = (is_paused()),
            end_day = end_day,
            end_hr = end_hr,
            end_min = end_min,
            end_sec = end_sec,
            is_on = (is_timer_on()),
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
                    end_day = end_day,
                    end_hr = end_hr,
                    end_min = end_min,
                    end_sec = end_sec,
                    is_on=(is_timer_on()),
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

        user_id = data["id"]
        new_email = data["new_email"]
        new_name = data["new_name"]

        #change the name in matches as well
        user_found = users_ref.where("user_id","==",user_id).get()

        if len(user_found) > 0:
            user_found = user_found[0].to_dict()

            #change the name in hunter matches
            matches_found_as_hunter = matches_ref.where("hunter_email","==", user_found["email"]).stream()
            matches_found_as_target = matches_ref.where("target_email","==",user_found["email"]).stream()

            for match in matches_found_as_hunter:
                match = match.to_dict()
                match["hunter_email"] = new_email
                matches_ref.document(match["id"]).update(match)

            for match in matches_found_as_target:
                match = match.to_dict()
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
            if(code_found[0] == "B"):
                return render_template("blaster_ability.html", logged_in = True)
            if(code_found[0] == "P"):
                return redirect("https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstleyVEVO", code=302)
        else:
            print('Invalid ability code attempt by', flask.session["user_info"]["email"])
            return render_template("invalid_ability_code.html")
    else:
        #TODO make this page
        return "Log in in order to gain new ability by clicking <a href='/auth/google'>here</a>"

@app.route('/change_bio', methods=['POST'])
def change_bio():
    if "user_info" in flask.session.keys():
        max_bio_len = 55
        if(len(request.json["bio"]) < 55):
            user_info = users_ref.where('email',"==", flask.session["user_info"]["email"]).get()[0].to_dict()
            user_info["bio"] = request.json["bio"]
            users_ref.document(user_info["user_id"]).update(user_info)
            return "Success"
        else:
            return "The text you entered is too long. It has to contain less than 55 characters."

@app.route('/report_issue', methods=['POST'])
def report_issue():
    if "user_info" in flask.session.keys():
        user_info = users_ref.where('email',"==", flask.session["user_info"]["email"]).get()[0].to_dict()
        user_email = user_info["email"]
        user_name = user_info["name"]
        user_id = user_info["user_id"]
        issue = request.json["issue"]

        email_title = "Splash - A user submitted a new issue"
        msg = Message(email_title, sender = 'reshwap2019@gmail.com', recipients = admins)
        
        msg.body = "User: {}\nemail: {}\nUser id: {}\n\nIssue: {}".format(user_name, user_email, user_id, issue)
        mail.send(msg)

        create_new_issue(user_email, issue)
        
        return "Your issue was successfully submitted."

@app.route('/ability/')
def ability_index():
    return render_template("invalid_ability_code.html")

@app.route('/pause_game', methods=['POST'])
def pause_game():
    if is_admin():
        pause = pause_ref.document("0").get().to_dict()
        pause["is_paused"] = not pause["is_paused"]
        pause_ref.document("0").update(pause)

        all_user_emails = [user["email"] for user in [user.to_dict() for user in users_ref.stream()]]

        print("hello")
        if pause["is_paused"]:
            # print(all_user_emails)
            # send_message(all_user_emails, "Splash has been paused!")
            return "Game paused"
        else:
            # print(all_user_emails)
            # send_message(all_user_emails, "Splash continues...")
            return "Game started"
    else:
        return "Access denied"

@app.route('/active_timer', methods=['POST'])
def active_timer():
    if is_admin():
        timer = pause_ref.document("1").get().to_dict()
        timer["is_on"] = not timer["is_on"]
        pause_ref.document("1").update(timer)

        if timer["is_on"]:
            now = datetime.now()
            timer["end_day"] = now.day + 1
            timer["end_hr"] =  now.hour
            timer["end_min"] = now.minute
            timer["end_sec"] = now.second
            pause_ref.document("1").update(timer)
            return "Timer on"
        else:
            return "Timer off"
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

# @app.route('/prank_ability', methods=['POST'])
# def qualify_user():
#     code_from_link = parse_code(request.json["link"])
#     #check if the code exists and that it's valid
#     if(is_logged_in() and len(codes_ref.where("code","==",code_from_link).where("used_at","==", "").get()) > 0):
#         return "https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstleyVEVO"
#     else:
#         return "Access denied, try logging in."


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


@app.route('/resolveIssue/<issue_id>')
def resolveIssue(issue_id):
    if is_admin():
        issue_found = issues_ref.where("id","==",issue_id).get()
        if len(issue_found) > 0:
            issue_found = issue_found[0].to_dict()
            issue_found["is_resolved"] = True
            issue_found["time_resolved"] = str(time_now())
            issue_found["admin_email"] = flask.session["user_info"]["email"]
            issues_ref.document(issue_found["id"]).update(issue_found)
        else:
            print("Issue not found")
            return "Issue not found"
        return redirect(url_for('index'))
    else:
        return "access denied"

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
            # delete_collection(stats_ref, 1)

            #create new pause variable
            pause_ref.document("0").set(pause_model())
            pause_ref.document("1").set(timer_model())
            immunity_ref.document("0").set(immunity_model())

            #gets the excel file from front-end
            arr = request.get_array(field_name='file')
            users=[]
            for u in arr:
                users.append({'name':u[0], 'email':str.lower(u[1])})

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
                yield "<div></div> All users uploaded, let the games begin!"
                yield "<div><button><a href="+ "/" + ">Take me back to admin page</a></button></div>"
            set_all_stats()
            return Response(generate(), mimetype='text/html')
    return redirect(url_for('index'))

@app.route('/generate_codes', methods=['POST'])
def generateCodes():
    if is_admin():
        # print("counting survivors")
        # all_users_alive = users_ref.where("time_eliminated", "==", "").get()

        # all_emails = []
        # for user in all_users_alive:
        #     all_emails.append(user.to_dict()["name"])
        
        # print(all_emails)

        # return "survivor list returned!!!"
        delete_collection(codes_ref, 50)
        
        create_new_code("I6427", 10)
        # create_new_code("I6136", 10)
        # create_new_code("I9308", 10)
        # create_new_code("I7059", 10)
        # create_new_code("I3953", 10)
        # create_new_code("I9507", 10)
        # create_new_code("I6634", 10)
        # create_new_code("I9285", 10)
        # create_new_code("I5062", 10)
        # create_new_code("I7617", 10)
        # create_new_code("I5487", 10)
        # create_new_code("I2283", 10)
        # create_new_code("I5693", 10)

        create_new_code("R4963", 10)
        # create_new_code("R2778", 10)
        # create_new_code("R3755", 10)
        # create_new_code("R8663", 10)
        # create_new_code("R3693", 10)
        # create_new_code("R5083", 10)
        # create_new_code("R5967", 10)
        # create_new_code("R9948", 10)

        create_new_code("Q2137", 10)
        # create_new_code("Q0237", 10)
        # create_new_code("Q4733", 10)

        # create_new_code("B3764", 10)
        # create_new_code("B1167", 10)
        # create_new_code("B0421", 10)
        # create_new_code("B9156", 10)
        # create_new_code("B6592", 10)
        # create_new_code("B3177", 10)

        return "Code generated!!!"
    else:
        return "Access denied"

# @app.route('/survivor_list', methods=['POST'])
# def ():
#     if is_admin():
#         print("counting survivors")
#         all_users_alive = users_ref.where("time_eliminated", "==", "").get()

#         all_emails = []
#         for user in all_users_alive:
#             all_emails.append(user.to_dict()["email"])
        
#         print(all_emails)

#         return "survivor list returned!!!"
#     else:
#         return "Access denied"


@app.route('/activate_24_hour_round', methods=['POST'])
def activate24():
    if is_admin():

        alive_count = 0
        dead_count = 0
        for user in users_ref.stream():
            user = user.to_dict()
            if(not within_24_hours(time_now(), user["time_of_last_elim"])):
                print(">>>>>")
                print(user["email"])
                print(">>>>>")
                eliminate_user(user["email"])
                dead_count +=1

            else:
                alive_count += 1

        for match in matches_ref.stream():
            match_dict = match.to_dict()
            if match_dict["time_ended"] == "":
                terminate_match(match_dict, reason="24-R")


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

@app.route('/rules')
def rules():
    return render_template("rules.html", logged_in=is_logged_in())

@app.route("/18652820686")
def secret_code():
    return render_template("secret_code.html")

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('500.html'), 404

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
