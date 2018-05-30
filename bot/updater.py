# coding: utf-8
import logging
from decouple import Config, RepositoryEnv
from telegram.ext import *

config = Config(RepositoryEnv('config.env'))
updater = Updater(token=config('TOKEN'))
dispatcher = updater.dispatcher

from .controllers.groups import *
from .controllers.notification import *


if not config('DEBUG', cast=bool):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=f'{updater.bot.name.lower()[1:]}.log',
        filemode='a+')
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def start(bot, update):
    update.effective_message.reply_text(
        f'Hello. I can /create groups for you and keep all your friends inside them. '
        f'You can call me anytime using inline mode via {bot.name} and pick those groups '
        f'to be printed in your messages.')


def help(bot, update):
    message = 'List of commands I am serving right now:\n'
    message += '/create - create a new group\n'
    if update.effective_user.id == update.effective_chat.id:
        message += '/groups - list of all of your groups'
    else:
        message += '/groups - list of all of chat groups'
    update.effective_message.reply_text(message)


def expired_session(bot, update):
    update.callback_query.answer('Session expired. Start again.')


def cancel(bot, update):
    update.effective_message.reply_text('Sure, what now? /help')
    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


# default commands
dispatcher.add_error_handler(error)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))

# inline mode
dispatcher.add_handler(InlineQueryHandler(inline_mode))
dispatcher.add_handler(ChosenInlineResultHandler(inline_chosen))

# mention all members
dispatcher.add_handler(CommandHandler('all', mention_all, pass_chat_data=True))

# creating groups
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('create', group_create)],
    states={
        CREATE_GROUP: [
            MessageHandler(Filters.text, group_create_complete)]},
    fallbacks=[CommandHandler('cancel', cancel)]))

# listing user's groups
dispatcher.add_handler(CommandHandler('groups', group_list))
dispatcher.add_handler(CallbackQueryHandler(group_open, pattern='group.list.', pass_user_data=True))

# joining/leaving the group
dispatcher.add_handler(CallbackQueryHandler(group_join, pattern='group.join.'))
dispatcher.add_handler(CallbackQueryHandler(group_leave, pattern='group.leave.'))

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
    fallbacks=[CommandHandler('cancel', cancel)],
    conversation_timeout=120))

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
    fallbacks=[CommandHandler('cancel', cancel)],
    conversation_timeout=60))

dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(group_copy_enter, pattern='group.copy.', pass_user_data=True)],
    states={
        GROUP_COPY: [
            CallbackQueryHandler(group_copy_complete, pass_user_data=True)]},
    fallbacks=[CommandHandler('cancel', cancel)],
    conversation_timeout=60))

# exiting from the group
dispatcher.add_handler(CallbackQueryHandler(group_exit, pattern='group.exit'))

# checking every message for mentioned groups
dispatcher.add_handler(MessageHandler(Filters.text, check_every_message))

# unexpected callback_queryies
dispatcher.add_handler(CallbackQueryHandler(expired_session))
