# coding: utf-8
from bot.updater import *
from bot.models import database, Group, GroupUsers


if __name__ == '__main__':
    database.create_tables([Group, GroupUsers])
    updater.start_polling()
    updater.idle()