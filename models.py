from flask_sqlalchemy import SQLAlchemy
from app import db

import time
from datetime import datetime
from pytz import timezone
from utils import generate_user_id


fmt = "%Y-%m-%d %H:%M:%S %Z%z"

def time_now():
    return datetime.now(timezone('US/Eastern')).strftime(fmt)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    
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

    def __init__(self, name, email):

        self.user_id = generate_user_id()
        self.name = name
        self.email = email

        self.number_of_elims = 0
        self.time_of_last_elim = None
        self.time_eliminated = None

        self.is_immune = 0
        self.time_immunity_activated = None
        self.immunity_duration = 0

        self.time_created = time_now()

        print('User created at time:', self.time_created)

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
            'time_created':self.time_created
        }

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.String(), primary_key=True)
    hunter_email = db.Column(db.String())
    target_email = db.Column(db.String())

    time_created = db.Column(db.String())
    time_ended = db.Column(db.String())

    reason = db.Column(db.String())

    def __init__(self, hunter_email, target_email):

        self.hunter_email = hunter_email
        self.target_email = target_email
        self.time_created = time_now()

        self.time_ended = None
        self.reason = None

        print('Match created at time:', self.time_created.strftime(fmt))

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
