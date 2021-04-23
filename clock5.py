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

def is_paused():
    is_paused = pause_ref.document("0").get().to_dict()["is_paused"]
    return is_paused

def is_immunity_on():
    is_immunity_on = immunity_ref.document("0").get().to_dict()["is_immunity_on"]
    return is_immunity_on

def get_leaderboard(n_users):
    leaderboard = users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).limit(n_users).get()
    return [user.to_dict() for user in leaderboard]

def get_table(table):
    return [doc.to_dict() for doc in table.stream()]

def get_basic_stats():

    stats = stats_ref.document("0").get().to_dict()
    n_users = stats["n_users"]
    n_matches = stats["n_matches"]
    n_users_alive = stats["n_users_alive"]
    n_matches_ongoing = stats["n_matches_ongoing"]

    return n_users, n_matches, n_users_alive, n_matches_ongoing

def get_all_stats():
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

def compute_ranks():

    all_users = [user.to_dict() for user in users_ref.order_by("number_of_elims",direction=firestore.Query.DESCENDING).get()]
    for i in range(0, len(all_users)):
        all_users[i]["rank"] = i
        users_ref.document(all_users[i]["user_id"]).update(all_users[i])

get_all_stats()
compute_ranks()
