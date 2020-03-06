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

@app.route('/')
def index():
    print(db)
    create_new_match("asdf", "asdf")
    create_new_user("asdf",'asdf')
    try:
        if(flask.session["user_info"]["email"] in admins):
            return render_template('admin.html',
            user_info=flask.session["user_info"],
            logged_in=True)
        else:
            return render_template('admin.html',
            user_info=flask.session["user_info"],
            logged_in=True)
    except:
        return render_template('index.html',
            logged_in=False)

@app.route('/upload', methods=['POST'])
def upload():
    if(flask.session['user_info']['email'] in admins):
        if request.method == 'POST':
            print(">>>>>>>>>")
            print("Upload activated")
            print(">>>>>>>>>")
            User.query.delete()
            Match.query.delete()
            # yield "<div></div>All users deleted - {}".format(n)
            arr = request.get_array(field_name='file')
            # yield "<div></div>Excel file received"
            users=[]
            for u in arr:
                users.append({'name':u[0], 'email':u[1]})
            random.shuffle(users)
            # yield "<div></div>Users parsed"
            def generate():
                for x in range(0,len(users)-1):
                    yield "<div></div>"+ str(x+1) +" out of "+ str(len(users)) + " users uploaded."
                    create_new_user(users[x]['name'], users[x]['email'])
                    create_new_match(users[x]['email'], users[x+1]['email'], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                create_new_user(users[len(users)-1]['name'], users[len(users)-1]['email'])
                create_new_match(users[len(users)-1]['email'], users[0]['email'], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                yield "<div></div> All users uploaded, let the games begin!"
                yield "<div><button><a href="">Take me back to admin page</a></button></div>"
            return Response(generate(),mimetype='text/html')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
