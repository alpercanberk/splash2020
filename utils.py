
import random
import string
import time

from datetime import datetime
from pytz import timezone

def gtd(generator):
    list = []
    for element in generator:
        n_dict = element.to_dict()
        n_dict['id'] = element.id
        list.append(n_dict)
    return list

def generate_user_id():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

fmt = "%Y-%m-%d %H:%M:%S"

def time_now():
    return datetime.now(timezone('US/Eastern')).strftime(fmt)

class Pause():
    def __init__(self):
        self.is_paused = False
    def switch():
        is_paused = not is_paused
    def get():
        return is_paused

a = "2020-03-08 21:22:14"
b = "2020-03-09 21:22:15"
c = "2020-03-09 21:22:13"

def find_time_difference(a,b):
    if(a=="" or b==""):
        return 999999

    a_datetime = datetime.strptime(a, fmt).timestamp()
    b_datetime = datetime.strptime(b, fmt).timestamp()

    return abs(a_datetime - b_datetime)

def within_24_hours(a,b):
    if find_time_difference(a,b) <= 86400:
        return True
    else:
        return False
