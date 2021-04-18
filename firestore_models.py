
import json

import time
from datetime import datetime
from pytz import timezone
from utils import generate_user_id, time_now


def user_model(name, email, id):
    return {
        "name":name,
        "email":email,
        "user_id":id,

        "number_of_elims":0,
        "time_of_last_elim":"",
        "time_eliminated":"",

        "is_immune":0,
        "time_immunity_activated":"",
        "immunity_duration":0,

        "time_created":str(time_now()),

        "num_revives":0,

        "codes_found":0,

        "rank":0
    }

def match_model(hunter_email, target_email, id):
    return {
        "id":id,

        "hunter_email":hunter_email,
        "target_email":target_email,

        "time_created":str(time_now()),
        "time_ended":"",

        "reason":""
    }

def pause_model():
    return {"is_paused":False}

def immunity_model():
    return {"is_immunity_on":True}

def stats_model():
    return {"all_stats": ""}

def announcements_model(title, content):
    return {
        "announcement_title":title,
        "announcement_content":content
    }

def code_model(code, duration):
    return {
        "code":code,
        "type":"",
        "duration":duration,
        "used_at":"",
        "used_by":"",
        "used_on":""
    }
