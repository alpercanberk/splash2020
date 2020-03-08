from flask import Flask, redirect, render_template, request, jsonify, url_for, Response
import flask
import flask_excel as excel

import datetime
import json
import os

import random

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

def create_new_user(name, email):
    print("User creation initialized")
    try:
        new_user = User(name, email)
        db.session.add(new_user)
        db.session.commit()
        print("User created")
        return "User created"
    except Exception as e:
        print("User creation failed")
        print(str(e))
        return str(e)

def create_new_match(hunter_email, target_email):
    try:
        new_match = Match(hunter_email, target_email)
        db.session.add(new_match)
        db.session.commit()
        print("Match created!")
    except Exception as e:
        print("Match creation failed")
        print(str(e))

def get_table(table):
    all_elements = table.query.all()
    return [e.serialize() for e in all_elements]

def get_basic_stats():
    n_users = len(get_table(User))
    n_matches = len(get_table(Match))

    return n_users, n_matches

def eliminate_user(email, increment_elimination_count=False):

    print("Eliminate user function activated")

    user_being_eliminated = User.query.filter_by(email=email).first()

    #check if the user exists
    print(user_being_eliminated)
    print(user_being_eliminated is not None)

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
        new_match = Match(hunter_of_user_email, target_of_user_email)
        db.session.add(new_match)
        print("New match created!")

        #kill the user
        user_being_eliminated.time_eliminated = time_now()

        db.session.commit()

        return "Elimination successful"
    else:
        return "User not found."

def add_user(name, email):

    #create a new user
    new_user = User(name, email)
    db.session.add(new_user)
    print("New user created!")

    all_elims = get_table(Match)
    elim_picked_id = all_elims[random.randint(0, len(all_elims))]["id"]
    elim_picked = Match.query.filter_by(id=elim_picked_id).first()

    elim_hunter_email = elim_picked.serialize()["hunter_email"]
    elim_target_email = elim_picked.serialize()["target_email"]

    #complete elim_picked
    elim_picked.time_ended = time_now()
    elim_picked.reason = "Added user"

    new_elim_1 = Match(elim_hunter_email, email)
    new_elim_2 = Match(email, elim_target_email)

    db.session.add(new_elim_1)
    db.session.add(new_elim_2)

    db.session.commit()

    return "New user created!"

def revive_user():

    #revive user

    #find a new random location in the chain

    #complete the elim with special reason and create two new elims to insert the new person

    return "ok"

def is_admin():
    if(flask.session["user_info"]["email"] in admins):
        return True
    return False

def is_paused():
    pause = Pause.query.first()
    return pause.serialize()

@app.route('/eliminate_user_admin', methods=["POST"])
def eliminate_user_admin_route():
    if(is_admin()):
        print("Eliminating a user...")
        data = request.json
        return eliminate_user(data["email"], data["increment_elimination_count"])
    else:
        return "Damn you're smart, come to programming club..."

@app.route('/eliminate_user', methods=["POST"])
def eliminate_user_route():
    print("Eliminating a user...")
    print(request.json)

@app.route('/')
def index():
    try:
        if(is_admin()):
            all_users = get_table(User)
            all_matches = get_table(Match)
            return render_template('admin.html',
            user_info = flask.session["user_info"],
            logged_in = True,
            user_table = all_users,
            match_table = all_matches,
            basic_stats = (get_basic_stats()),
            is_paused = (is_paused())
            )
        else:
            user_found = User.query.filter_by(email=flask.session["user_info"]["email"]).first()
            if user_found is not None:
                return render_template('home.html',
                user_info=user_found.serialize(),
                target_info=Match.query.filter_by(hunter_email=flask.session["user_info"]["email"]).first().serialize(),
                logged_in=True
                )
            else:
                return render_template('not_logged.html',
                    logged_in=True)
    except Exception as e:
        print(e)
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

        user_found = User.query.filter_by(name=previous_name).filter_by(email=previous_email).first()
        if user_found is not None:
            user.email = new_email
            user.name = new_name
            db.session.commit()
            print("User edit successful")
            return "User edit successful"
        else:
            print("User not found")
            return "User not found"
    else:
        return "Access denied"

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

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
