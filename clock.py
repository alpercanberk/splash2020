
from apscheduler.schedulers.background import BackgroundScheduler
from models import *

def get_all_stats():

    print(">>>>>>")
    print(Stats.query.first())
    print(">>>>>>")

    # try:
    #     n_users, n_matches, n_users_alive, n_matches_ongoing = get_basic_stats()
    #
    #     leaderboard = get_leaderboard(10)
    #
    #     number_of_codes_in_game = len(Code.query.all())
    #     number_of_codes_activated = len(Code.query.filter_by(used_at=None).all())
    #
    #     code_leaderboard = User.query.order_by(User.codes_found.desc()).limit(3).all()
    #     code_leaderboard = [user.serialize() for user in code_leaderboard]
    #
    #     # qualified_board = [user.serialize() for user in User.query.filter("-Q*" in User.name).all()]
    #
    #     immunity_board = [user.serialize() for user in User.query.filter(User.immunity_duration != 0).all()]
    #
    #     Stats.query.first().stats = str({
    #         "n_users":n_users,
    #         "n_matches":n_matches,
    #         "n_users_alive":n_users_alive,
    #         "n_matches_ongoing":n_matches_ongoing,
    #         "leaderboard":leaderboard,
    #         "number_of_codes_in_game":number_of_codes_in_game,
    #         "number_of_codes_activated":number_of_codes_activated,
    #         "code_leaderboard":code_leaderboard,
    #         # "qualified_board":qualified_board,
    #         "immunity_board":immunity_board,
    #         "is_paused": (is_paused()),
    #         "is_immunity_on":(is_immunity_on())
    #         })
    # except:
    #     Stats.query.first().stats = ""


def wear_down_immunity():
    users_with_immunity = User.query.filter_by(User.immunity_duration != 0).all()
    try:
        if(users_with_immunity is not None):
            for immune_user in users_with_immunity:
                immune_user.immunity_duration -= 1
            db.session.commit()
    except:
        pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=wear_down_immunity, trigger="interval", seconds=10)
scheduler.add_job(func=get_all_stats, trigger="interval", seconds=10)
scheduler.start()
