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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
#register blueprints for routes
app.register_blueprint(routes)
#setup the database
db = SQLAlchemy(app)
#setup secret key for oauth2
app.secret_key = os.environ['SECRET_KEY']

from models import *

@scheduler.scheduled_job('interval', seconds=10)
def get_all_stats():
    print("Get all stats works")
    print(Stats.query.first())
    print(">>>>>>")

        # try:
        #     n_users, n_matches, n_users_alive, n_matches_ongoing = get_basic_stats()
        #
        #     leaderboard = get_leaderboard(10)
        #
        #     number_of_codes_in_game =len(Code.query.all())
        #     number_of_codes_activated = len(Code.query.filter_by(used_at=None).all())
        #
        #     code_leaderboard = User.query.order_by(User.codes_found.desc()).limit(3).all()
        #     code_leaderboard = [user.serialize() for user in code_leaderboard]
        #
        #     # qualified_board = [user.serialize() for user in User.query.filter("-Q*" in User.name).all()]
        #
        #     immunity_board = [user.serialize() for user in User.query.filter(User.immunity_duration != 0).all()]
        #
        #     Stats.query.first().stats = str({
        #         "n_users":n_users,
        #         "n_matches":n_matches,
        #         "n_users_alive":n_users_alive,
        #         "n_matches_ongoing":n_matches_ongoing,
        #         "leaderboard":leaderboard,
        #         "number_of_codes_in_game":number_of_codes_in_game,
        #         "number_of_codes_activated":number_of_codes_activated,
        #         "code_leaderboard":code_leaderboard,
        #         # "qualified_board":qualified_board,
        #         "immunity_board":immunity_board,
        #         "is_paused": (is_paused()),
        #         "is_immunity_on":(is_immunity_on())
        #         })
        # except:
        #     Stats.query.first().stats = ""

@scheduler.scheduled_job('interval', seconds=10)
def wear_down_immunity():
    print("Immunity works")
    users_with_immunity = User.query.filter_by(User.immunity_duration != 0).all()
    if(users_with_immunity is not None):
        for immune_user in users_with_immunity:
            immune_user.immunity_duration -= 1
        db.session.commit()

scheduler.add_job(func=wear_down_immunity, trigger="interval", seconds=10)
scheduler.add_job(func=get_all_stats, trigger="interval", seconds=10)
scheduler.start()
