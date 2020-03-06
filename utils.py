
import random
import string
import datetime

def gtd(generator):
    list = []
    for element in generator:
        n_dict = element.to_dict()
        n_dict['id'] = element.id
        list.append(n_dict)
    return list

def generate_user_id():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))


class Pause():
    def __init__(self):
        self.is_paused = False
    def switch():
        is_paused = not is_paused
    def get():
        return is_paused
