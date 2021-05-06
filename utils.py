
import random
import string
import time

from datetime import datetime
from pytz import timezone

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.message import EmailMessage
from jinja2 import Template

import os
import smtplib

def gtd(generator):
    list = []
    for element in generator:
        n_dict = element.to_dict()
        n_dict['id'] = element.id
        list.append(n_dict)
    return list

def generate_user_id():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

def generate_random_id():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

def send_message(user_emails, announcement):

    content = ""

    message_template = Template(content)
    message = message_template.render()

    mail = smtplib.SMTP('smtp.googlemail.com', 587)

    mail.ehlo()
    mail.starttls()
    mail.login(os.environ["EMAIL_USERNAME"], os.environ["EMAIL_PASSWORD"])

    msg = MIMEMultipart()

    msg['From'] = "hi"
    msg["Bcc"] = ", ".join(user_emails)
    print(user_emails)
    msg['Subject'] = announcement + " --- " + str(time_now())[-8:]
    msg.attach(MIMEText("", 'html'))


    mail.send_message(msg)
    del msg

    mail.close()

    print('A message is sent\n\n')

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
