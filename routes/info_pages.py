
from . import routes

from flask import Flask, redirect, render_template, request, jsonify, url_for
from flask import render_template
import flask

import google.oauth2.credentials
import google_auth_oauthlib.flow

import datetime
import json

import os
import random

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lists import Lists

@routes.route('/team')
def team():
    return render_template("team.html")

@routes.route('/hof')
def hof():
    return render_template("hof.html")

