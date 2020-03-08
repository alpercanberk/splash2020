
import random
import string

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
