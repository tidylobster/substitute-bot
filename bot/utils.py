from pyrogram import Client
from .updater import config


def client_wrapper(func):
    def wrapper(*args, **kwargs):
        app = Client(
            session_name="my_account",
            api_id=config('API_ID'),
            api_hash=config('API_HASH'))
        app.start()
        kwargs.update({'app': app})
        result = func(*args, **kwargs)
        app.stop()

        return result
    return wrapper
