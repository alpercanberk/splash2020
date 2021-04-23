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

def wear_down_immunity():
    # print("Immunity works")
    users_with_immunity = users_ref.where("immunity_duration", ">", 0).get()
    if(len(users_with_immunity) > 0):
        for immune_user in users_with_immunity:
            immune_user = immune_user.to_dict()
            immune_user["immunity_duration"] -= 1
            users_ref.document(immune_user["user_id"]).update(immune_user)

wear_down_immunity()
print("1 minute interval clock executed")
