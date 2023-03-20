from flask_sqlalchemy import SQLAlchemy
from app import db
import json

import time
from datetime import datetime
from pytz import timezone
from utils import generate_user_id, time_now



def user_model(name, email, user_id):
    return {
        "name":name,
        "email":email,
        "user_id":user_id,

        "number_of_elims":0,
        "time_of_last_elim":"",
        "time_eliminated":"",

        "is_immune":0,
        "time_immunity_activated":"",
        "immunity_duration":"",

        "time_created":str(time.now()),

        "num_revives":0,

        "codes_found":0,

        "rank":0
    }


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(), primary_key=True)

    user_id = db.Column(db.String())
    name = db.Column(db.String())
    email = db.Column(db.String())

    number_of_elims = db.Column(db.Integer)
    time_of_last_elim = db.Column(db.String())
    time_eliminated = db.Column(db.String())

    is_immune = db.Column(db.Integer)
    time_immunity_activated = db.Column(db.String())
    immunity_duration = db.Column(db.Integer)

    time_created = db.Column(db.String())

    num_revives = db.Column(db.Integer)

    codes_found = db.Column(db.Integer)

    rank = db.Column(db.Integer)

    def __init__(self, name, email):

        self.id = generate_user_id()
        self.name = name
        self.email = email

        self.number_of_elims = 0
        self.time_of_last_elim = ""
        self.time_eliminated = ""

        self.is_immune = 0
        self.time_immunity_activated = ""
        self.immunity_duration = 0

        self.time_created = time_now()

        self.num_revives = 0
        self.codes_found = 0
        self.rank = 0

    def __repr__(self):
        return '<user {} {}>'.format(self.id, self.email)

    def serialize(self):
        return {
            'id':self.id,
            'name':self.name,
            'email':self.email,
            'number_of_elims':self.number_of_elims,
            'time_of_last_elim':self.time_of_last_elim,
            'time_eliminated':self.time_eliminated,
            'is_immune':self.is_immune,
            'time_immunity_activated':self.time_immunity_activated,
            'immunity_duration':self.immunity_duration,
            'time_created':self.time_created,
            'num_revives':self.num_revives,
            'codes_found':self.codes_found,
            'rank':self.rank
        }

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    hunter_email = db.Column(db.String())
    target_email = db.Column(db.String())

    time_created = db.Column(db.String())
    time_ended = db.Column(db.String())

    reason = db.Column(db.String())

    def __init__(self, hunter_email, target_email):

        self.hunter_email = hunter_email
        self.target_email = target_email
        self.time_created = time_now()
        self.time_ended = ""
        self.reason = ""

    def __repr__(self):
        return '<match {}>'.format(self.id)

    def serialize(self):
        return {
            'id':self.id,
            'hunter_email':self.hunter_email,
            'target_email':self.target_email,
            'time_created':self.time_created,
            'time_ended':self.time_ended,
            'reason':self.reason
        }

class Pause(db.Model):
    __tablename__ = 'pause'

    id = db.Column(db.Integer, primary_key=True)
    is_paused = db.Column(db.Boolean)

    def __init__(self):
        self.is_paused = False

    def __repr__(self):
        return '< pause in state ' + str(self.is_paused) + ' >'

    def serialize(self):
        return self.is_paused

class Immunity(db.Model):
    __tablename__ = 'immunity'

    id = db.Column(db.Integer, primary_key=True)
    is_immunity_on = db.Column(db.Boolean)

    def __init__(self):
        self.is_immunity_on = True

    def __repr__(self):
        return '< immunity in state ' + str(self.is_immunity_on) + ' >'

    def serialize(self):
        return self.is_immunity_on

# class Issue(db.Model):
#     __tablename__ = 'issues'

#     id = db.Column(db.Integer, primary_key=True)
#     is_resolved = db.Column(db.Boolean)
#     user_email = db.Column(db.String())
#     admin_email = db.Column(db.String())
#     content = db.Column(db.String())
#     time_created = db.Column(db.String())

#     def __init__(self, user_email, content):
#         self.is_resolved = False
#         self.user_email = user_email
#         self.admin_email = ""
#         self.content = content
#         self.time_created = time_now()

#     def __repr__(self):
#         return 'issue'

#     def serialize(self):
#         return {
#         "user":self.user_email,
#         "content":self.content
#         }


class Stats(db.Model):
    __tablename__ = 'stats'

    id = db.Column(db.Integer, primary_key=True)
    stats = db.Column(db.String())

    def __init__(self):
        self.stats = ""

    def __repr__(self):
        return '< stats >'

    def serialize(self):
        return self.stats.replace("'","\"")

class Announcements(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    announcement_title = db.Column(db.String())
    announcement_content = db.Column(db.String())

    def __init__(self):
        self.announcement_title = ""
        self.announcement_content = ""

    def __repr__(self):
        return '< announcement >'

    def serialize(self):
        return {
        "title":self.announcement_title,
        "content":self.announcement_content
        }


class Code(db.Model):
    __tablename__ = "codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String())
    type = db.Column(db.String())
    duration =db.Column(db.Integer())
    used_at = db.Column(db.String())
    used_by = db.Column(db.String())
    used_on = db.Column(db.String())

    def __init__(self):
        self.used_at = ""

    def serialize(self):
        return {
            "id":self.id,
            "code":self.code,
            "used_at":self.used_at,
            "used_by":self.used_by,
            "used_on":self.used_on,
            "duration":self.duration
        }
