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
        '/create - create a new group\n'
        '/groups - list of all of your groups')


def expired_session(bot, update):
    update.callback_query.answer('Session expired. Start again.')


def cancel(bot, update):
    update.effective_message.reply_text('Sure, what now? /help')
    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


# defaults
dispatcher.add_error_handler(error)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))

# inline mode
dispatcher.add_handler(InlineQueryHandler(inline_mode))

# creating groups
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('create', group_create)],
    states={
        CREATE_GROUP: [
            MessageHandler(Filters.text, group_create_complete)]},
    fallbacks=[CommandHandler('cancel', cancel)]))

dispatcher.add_handler(CommandHandler('groups', group_list))
dispatcher.add_handler(CallbackQueryHandler(group_open, pattern='group.list.', pass_user_data=True))

# adding members
dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_add_members_enter, pattern='group.add.', pass_user_data=True)],
    states={
        GROUP_ADD_MEMBERS: [
            CommandHandler('done', group_add_members_complete, pass_user_data=True),
            MessageHandler(Filters.text, group_add_members, pass_user_data=True)]},
    fallbacks=[CommandHandler('cancel', cancel)]))

# removing members
dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_remove_enter, pattern='group.remove.', pass_user_data=True)],
    states={
        GROUP_REMOVE_MEMBERS: [
            CallbackQueryHandler(group_remove_exit, pattern='group.remove.exit', pass_user_data=True),
            CallbackQueryHandler(group_remove_members, pattern='group.remove.member.', pass_user_data=True)]},
    fallbacks=[CommandHandler('cancel', cancel)], conversation_timeout=120))

# renaming groups
dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_rename_enter, pattern='group.rename.', pass_user_data=True)],
    states={
        GROUP_RENAME: [
            MessageHandler(Filters.text, group_rename_complete, pass_user_data=True)]},
    fallbacks=[CommandHandler('cancel', cancel)]))

# deleting groups
dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_delete_enter, pattern='group.delete.', pass_user_data=True)],
    states={
        GROUP_DELETE: [
            CallbackQueryHandler(group_delete_complete, pass_user_data=True)]},
    fallbacks=[CommandHandler('cancel', cancel)], conversation_timeout=60))

dispatcher.add_handler(CallbackQueryHandler(group_exit, pattern='group.exit'))

# unexpected callback_queryies
dispatcher.add_handler(CallbackQueryHandler(expired_session))
