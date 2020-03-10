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

from flask_sslify import SSLify
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["DATABASE_URL"]
#register blueprints for routes
app.register_blueprint(routes)
#initialize the excel module
excel.init_excel(app)
#setup the database
db = SQLAlchemy(app)
#setup secret key for oauth2
app.secret_key = os.environ['SECRET_KEY']

from models import *

def expire_ability(code, used_by, used_on):
    ability = Code.query.filter_by(code=code).first()

    if(ability is not None):
        ability.used_at = time_now()
        ability.used_on = used_on
        ability.used_by = used_by

        user = User.query.filter_by(email=used_by).first()
        if(user is not None):
            user.codes_found += 1

        db.session.commit()
    else:
        print("Something went wrong...")

def create_new_user(name, email):
    print("User creation initialized")
    try:
        new_user = User(name, email)
        db.session.add(new_user)
        db.session.commit()
        # print("User created")
        return "User created"
    except Exception as e:
        # print("User creation failed")
        print(str(e))
        return str(e)

def create_new_match(hunter_email, target_email):
    try:
        new_match = Match(hunter_email, target_email)
        db.session.add(new_match)
        db.session.commit()
        # print("Match created!")
    except Exception as e:
        # print("Match creation failed")
        print(str(e))

def get_table(table):
    all_elements = table.query.all()
    return [e.serialize() for e in all_elements]

def get_basic_stats():
    n_users = len(get_table(User))
    n_matches = len(get_table(Match))
    n_users_alive = len(User.query.filter_by(time_eliminated="").all())
    n_matches_ongoing = len(Match.query.filter_by(time_ended="").all())

    return n_users, n_matches, n_users_alive, n_matches_ongoing

def get_leaderboard(n_users):
    leaderboard = User.query.order_by(User.number_of_elims.desc()).limit(n_users).all()
    return [user.serialize() for user in leaderboard]

def eliminate_user(email, increment_elimination_count=False):

    print("Eliminate user function activated")

    user_being_eliminated = User.query.filter_by(email=email).first()

    #check if the user exists

    if(user_being_eliminated is not None):
        user_active_match_hunter = Match.query.filter_by(hunter_email=email).filter_by(time_ended="").first()

        target_of_user_email = user_active_match_hunter.serialize()["target_email"]
        target_of_user = User.query.filter_by(email=target_of_user_email).first()

        user_active_match_target = Match.query.filter_by(target_email=email).filter_by(time_ended="").first()

        hunter_of_user_email = user_active_match_target.serialize()["hunter_email"]
        hunter_of_user = User.query.filter_by(email=hunter_of_user_email).first()

        print("target of user", target_of_user.serialize())
        print("hunter of user", hunter_of_user.serialize())

        #increment elimination count of the hunter of this user if needed
        if increment_elimination_count:
            hunter_of_user.number_of_elims += 1
            hunter_of_user.time_of_last_elim = time_now()
            print("Incremented elimination count")
        else:
            print("Didn't increment elimination count")

        #complete both hunter and target elims with the given reason
        user_active_match_hunter.time_ended = time_now()
        user_active_match_hunter.reason = "Hunter died"
        user_active_match_target.time_ended = time_now()
        if increment_elimination_count:
            user_active_match_target.reason = "Elimination"
        else:
            user_active_match_target.reason = "DQ"

        #pair up hunter and the target and create a new elim
        create_new_match(hunter_of_user_email, target_of_user_email)
        print("New match created!")

        #kill the user
        user_being_eliminated.time_eliminated = time_now()

        db.session.commit()

        return "Elimination successful"
    else:
        return "User not found."

def is_admin():
    if(flask.session["user_info"]["email"] in admins):
        return True
    return False

def is_logged_in():
    user_found = User.query.filter_by(email=flask.session["user_info"]["email"]).first()
    if user_found is not None:
        return True
    return False

def is_paused():
    pause = Pause.query.first()
    return pause.serialize()

def is_immunity_on():
    immunity = Immunity.query.first()
    return immunity.serialize()

def grant_immunity(email, minutes):
    user_found = User.query.filter_by(email=email).filter_by(time_eliminated="").first()
    if user_found is not None:
        user_found.immunity_duration += int(minutes)
        db.session.commit()
        return True
    else:
        return False

def insert_into_chain(email, reason):

    #find all matches that are currently active
    all_matches = [match.serialize() for match in Match.query.filter_by(time_ended="").all()]

    match_picked_id = all_matches[random.randint(0, len(all_matches))]["id"]
    match_picked = Match.query.filter_by(id=match_picked_id).first()

    match_hunter_email = match_picked.serialize()["hunter_email"]
    match_target_email = match_picked.serialize()["target_email"]

    #complete elim_picked
    match_picked.time_ended = time_now()
    match_picked.reason = reason

    create_new_match(match_hunter_email, email)
    create_new_match(email, match_target_email)

def revive_user(email):
    user_found = User.query.filter_by(email=email).filter(User.time_eliminated != "").first()
    if user_found is not None:
        user_found.time_eliminated = ""
        user_found.num_revives += 1
        insert_into_chain(user_found.serialize()["email"], "Revive")
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

    current_match = Match.query.filter_by(hunter_email=flask.session["user_info"]["email"]).filter_by(time_ended="").first()

    if current_match is not None:
        current_target_email = current_match.serialize()["target_email"]
        current_target_id = User.query.filter_by(email=current_target_email).first().serialize()["id"]
        current_target_immunity_duration = User.query.filter_by(email=current_target_email).first().serialize()["immunity_duration"]
        if not is_paused():
            if(code == current_target_id):
                if(current_target_immunity_duration <= 0 or (not is_immunity_on())):
                    eliminate_user(current_target_email, True)
                    return "Success!"
                else:
                    return "The code is correct, but your target seems to have immunity on.\
                    If they activated their immuninty in front of you,\
                    notify the Splashmasters because they are not allowed to do that"
            else:
                return "Invalid code, try again. (ps. There are 2 trillion possible combinations)"
        else:
            return "Chill out, the game is paused"
    else:
        return "Oops, something went wrong. Contact the admins about this."

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
    if "user_info" in flask.session.keys():
        if(is_admin()):
            all_users = get_table(User)
            all_matches = get_table(Match)
            return render_template('admin.html',
            user_info = flask.session["user_info"],
            logged_in = True,
            user_table = all_users,
            match_table = all_matches,
            basic_stats = (get_basic_stats()),
            is_paused = (is_paused()),
            codes_table = (get_table(Code))
            )
        else:
            user_found = User.query.filter_by(email=flask.session["user_info"]["email"]).first()
            if user_found is not None:
                if user_found.serialize()["time_eliminated"] == "":
                    current_match_of_user = Match.query.filter_by(hunter_email=flask.session["user_info"]["email"]).filter_by(time_ended="").first().serialize()
                    target_info = User.query.filter_by(email=current_match_of_user["target_email"]).first()
                    return render_template('home.html',
                    user_info=user_found.serialize(),
                    target_info=target_info.serialize(),
                    logged_in=True,
                    is_paused=(is_paused()),
                    is_immunity_on=(is_immunity_on())
                    )
                else:
                    return render_template('eliminated.html', logged_in=True)
            else:
                return render_template('not_logged.html',
                    logged_in=True)
    else:
        return render_template('index.html',
            logged_in=False)

@app.route('/edit_user', methods=['POST'])
def edit_user():
    print("Endpoint activated")
    if(is_admin()):
        print("Editing user...")
        data = request.json

        previous_email = data["previous_email"]
        previous_name = data["previous_name"]
        new_email = data["new_email"]
        new_name = data["new_name"]

        #change the name in matches as well
        user_found = User.query.filter_by(name=previous_name).filter_by(email=previous_email).first()

        if user_found is not None:

            #change the name in hunter matches
            matches_found_as_hunter = Match.query.filter_by(hunter_email=user_found.email).all()
            matches_found_as_target = Match.query.filter_by(target_email=user_found.email).all()

            for match in matches_found_as_hunter:
                match.hunter_email = new_email

            for match in matches_found_as_target:
                match.target_email = new_email

            user_found.email = new_email
            user_found.name = new_name

            db.session.commit()
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
        code = Code.query.filter_by(code=code).filter_by(used_at=None).first()
        if(code is not None):
            code_found = code.serialize()["code"]
            print('Someone found a code!')
            if(code_found[0] == "R"):
                return render_template("revive_ability.html", logged_in = True)
            if(code_found[0] == "I"):
                return render_template("immunity_ability.html", logged_in = True, duration=code.serialize()["duration"])
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
        pause = Pause.query.first()
        pause.is_paused = not pause.serialize()
        db.session.commit()
        if pause.serialize():
            return "Game paused"
        else:
            return "Game started"
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
    if(is_logged_in() and (Code.query.filter_by(code=code_from_link).first() is not None)):
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
    if(is_logged_in() and (Code.query.filter_by(code=code_from_link).filter_by(used_at=None).first() is not None)):
        print("Someone is qualifying for the final...")
        user_found = User.query.filter_by(email=flask.session["user_info"]["email"]).first()
        eliminate_user(flask.session["user_info"]["email"])
        user_found.name = user_found.name + " -Q*"
        expire_ability(code=code_from_link, used_by=flask.session["user_info"]["email"], used_on=flask.session["user_info"]["email"])
        return "Qualified!"
    else:
        return "Access denied, try logging in."

@app.route('/immunity_ability', methods=['POST'])
def immunity_ability():
    code_from_link = parse_code(request.json["link"])
    code = Code.query.filter_by(code=code_from_link).filter_by(used_at=None).first()
    #check if the code exists and that it's valid
    if(is_logged_in() and (code is not None)):
        if(grant_immunity(request.json["email"], code.serialize()["duration"])):
            print("Someone is activating their immunity ability")
            expire_ability(code=code_from_link, used_by=flask.session["user_info"]["email"], used_on=request.json["email"])
            return "Immunity granted!"
        else:
            return "Oops, something went wrong. Check the validity of your input."
    else:
        return "Access denied, try logging in."

@app.route('/shuffle_game', methods=['POST'])
def shuffle_game():
    if is_admin():

        all_matches = Match.query.all()
        for match in all_matches:
            match.time_ended = time_now()
            match.reason = "Game shuffled"

        #finds all alive users and shuffles their emails
        all_users = User.query.filter_by(time_eliminated="").all()
        all_emails = []
        for user in all_users:
            all_emails.append(user.serialize()["email"])
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

        db.session.commit()

        return "New user created!"
    else:
        return "Access denied"

@app.route('/upload', methods=['POST'])
def upload():
    if(is_admin()):
        if request.method == 'POST':
            print(">>>>>>>>>")
            print("Upload activated")
            print(">>>>>>>>>")

            #clears the database
            db.metadata.clear()
            User.query.delete()
            Match.query.delete()
            Pause.query.delete()

            #create new pause variable
            db.session.add(Pause())
            db.session.add(Immunity())
            db.session.add(Stats())

            #gets the excel file from front-end
            arr = request.get_array(field_name='file')
            users=[]
            for u in arr:
                users.append({'name':u[0], 'email':u[1]})

            #shuffle the list of users
            random.shuffle(users)

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

            return Response(generate(), mimetype='text/html')
    return redirect(url_for('index'))

@app.route('/activate_24_hour_round', methods=['POST'])
def activate24():
    if is_admin():

        all_matches = Match.query.all()
        for match in all_matches:
            match.time_ended = time_now()
            match.reason = "24-R"

        #find a more efficient way to do this, I can't pass custom functions in to filter :( something such as:
        # users_without_elim = User.query.filter(not within_24_hours(time_now(), User.time_of_last_elim)).all()
        # n_eliminated = len(users_without_elim)
        # for user in users_without_elim:
        #     user.time_eliminated = time_now()

        all_users = get_table(User)
        users_without_elim_emails = []
        for user in all_users:
            if not within_24_hours(user["time_of_last_elim"], time_now()):
                users_without_elim_emails.append(user["email"])

        all_users_without_elim = User.query.filter(User.email.in_(users_without_elim_emails)).all()
        n_eliminated = len(all_users_without_elim)
        for user in all_users_without_elim:
            user.time_eliminated = time_now()

        all_users = User.query.filter_by(time_eliminated="").all()
        all_emails = []
        for user in all_users:
            all_emails.append(user.serialize()["email"])
        random.shuffle(all_emails)

        def generate():
            yield "<div>{} users eliminated as a result of the 24-hour round</div>".format(n_eliminated)
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

# @app.route('/get_all_stats')
# def all_stats_route():
#     return str(Stats.query.first().serialize())

if __name__ == '__main__':
    # get_all_stats()
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
