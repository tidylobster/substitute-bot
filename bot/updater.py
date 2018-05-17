# coding: utf-8
import logging
from decouple import Config, RepositoryEnv
from telegram.ext import *

from .groups import *
from .inlinequery import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config(RepositoryEnv('config.env'))
updater = Updater(token=config('TOKEN'), request_kwargs={
    'proxy_url': 'socks5://163.172.152.192:1080',
})
dispatcher = updater.dispatcher


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


dispatcher.add_error_handler(error)
dispatcher.add_handler(InlineQueryHandler(substitute_query))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('create', group_create)],
    states={
        CREATE_GROUP: [MessageHandler(Filters.text, group_create_complete)]
    },
    fallbacks=[]))

dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('change', group_change)],
    states={
        GROUP_CHANGE: [CallbackQueryHandler(group_action, pattern='group.change.')],
        GROUP_ACTION: [CallbackQueryHandler(group_action_select, pattern='group.', pass_user_data=True)],
        GROUP_ADD_MEMBERS: [CommandHandler('done', group_add_members_done, pass_user_data=True),
                            MessageHandler(Filters.text, group_add_members, pass_user_data=True)],
        GROUP_MEMBER_REMOVE: [CallbackQueryHandler(group_member_exit, pattern='group.member.exit', pass_user_data=True),
                              CallbackQueryHandler(group_member_remove_complete, pattern='group.member.remove.', pass_user_data=True)]
    },
    fallbacks=[]))
