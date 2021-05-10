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


def create_new_code(code, duration):
    print("Code creation initialized")
    # try:
    id = code
    new_code = code_model(code, duration)
    codes_ref.document(id).set(new_code)

    return "Code created"
