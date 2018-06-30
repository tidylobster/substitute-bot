from .updater import config
from pyrogram import Client
from pyrogram.api.errors import error


def client_wrapper(func):
    def wrapper(*args, **kwargs):
        app = Client(
            session_name="my_account",
            api_id=config('API_ID'),
            api_hash=config('API_HASH'))
        app.start()

        result = None
        try:
            kwargs.update({'app': app})
            result = func(*args, **kwargs)
        finally:
            app.stop()

        return result
    return wrapper
