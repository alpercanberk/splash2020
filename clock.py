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

from firebase_admin import credentials, firestore, initialize_app

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["DATABASE_URL"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
#register blueprints for routes
app.register_blueprint(routes)
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

def is_paused():
    is_paused = pause_ref.document("0").get().to_dict()["is_paused"]
    return is_paused

def is_immunity_on():
    is_paused = immunity_ref.document("0").get().to_dict()["is_paused"]
    return is_paused

def get_leaderboard(n_users):
    leaderboard = users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).limit(n_users).get()
    return [user.dict() for user in leaderboard]

def get_table(table):
    return [doc.to_dict() for doc in table.stream()]

def get_basic_stats():

    n_users = len(get_table(users_ref))
    n_matches = len(get_table(matches_ref))
    n_users_alive = len(users_ref.where("time_eliminated","==","").get())
    n_matches_ongoing = len(matches_ref.where("time_ended","==", "").get())

    return n_users, n_matches, n_users_alive, n_matches_ongoing

def get_all_stats():
    n_users, n_matches, n_users_alive, n_matches_ongoing = get_basic_stats()

    leaderboard = get_leaderboard(10)

    number_of_codes_in_game =len(codes_ref.get())
    number_of_codes_activated = len(codes_ref.where("used_at","==","").get())

    code_leaderboard = users_ref.order_by(User.codes_found.desc()).limit(3).all()
    code_leaderboard = [user.serialize() for user in code_leaderboard]

    # qualified_board = [user.serialize() for user in User.query.filter("-Q*" in User.name).all()]

    immunity_board = [user.serialize() for user in User.query.filter(User.immunity_duration != 0).all()]

    fmt = "%Y-%m-%d %H:%M:%S"

    recent_elims = 0
    for elim in Match.query.all():
        if(within_24_hours(elim.serialize()["time_ended"], datetime.now().strftime(fmt))):
            recent_elims += 1

    print(">>>>>>")
    print(recent_elims)
    print(">>>>>>")

    Stats.query.first().stats = str({
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


def wear_down_immunity():
    # print("Immunity works")
    users_with_immunity = User.query.filter(User.immunity_duration > 0).all()
    if(users_with_immunity is not None):
        for immune_user in users_with_immunity:
            immune_user.immunity_duration -= 1
        db.session.commit()

get_all_stats()
wear_down_immunity()
