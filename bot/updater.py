# coding: utf-8
import logging
from decouple import Config, RepositoryEnv
from telegram.ext import *

from .groups import *
from .inlinequery import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config(RepositoryEnv('config.env'))
updater = Updater(token=config('TOKEN'))
dispatcher = updater.dispatcher


def start(bot, update):
    update.effective_message.reply_text(
        'Hello. I can /create groups for you and keep all your friends inside them. '
        'You can call me anytime using inline mode via @substitute_bot and pick those groups '
        'to be printed in your messages.')
    update.effective_message.reply_text('Try now!')


def help(bot, update):
    update.effective_message.reply_text(
        '/create - create new groups\n'
        '/change - adjust created groups')


def cancel(bot, update):
    update.effective_message.reply_text('Sure, what now? /help')
    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


dispatcher.add_error_handler(error)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(InlineQueryHandler(substitute_query))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('create', group_create)],
    states={
        CREATE_GROUP: [MessageHandler(Filters.text, group_create_complete)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]))

dispatcher.add_handler(CommandHandler('change', group_change))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_action, pattern='group.change.')],
    states={
        GROUP_ACTION: [CallbackQueryHandler(group_action_select, pattern='group.', pass_user_data=True)],
        GROUP_ADD_MEMBERS: [CommandHandler('done', group_add_members_done, pass_user_data=True),
                            MessageHandler(Filters.text, group_add_members, pass_user_data=True)],
        GROUP_MEMBER_REMOVE: [CallbackQueryHandler(group_member_exit, pattern='group.member.exit', pass_user_data=True),
                              CallbackQueryHandler(group_member_remove_complete, pattern='group.member.remove.', pass_user_data=True)],
        GROUP_RENAME: [MessageHandler(Filters.text, group_rename_complete, pass_user_data=True)],
        GROUP_DELETE: [CallbackQueryHandler(group_delete_complete, pass_user_data=True)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]))
