# coding: utf-8
import logging
from uuid import uuid4
from decouple import Config, RepositoryEnv

from telegram.ext import *
from telegram.utils.helpers import escape_markdown
from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode

from .groups import *

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


def stub(bot, update):
    update.callback_query.answer()
    update.effective_message.reply_text("You reached stub. Exiting...")
    return ConversationHandler.END


@database.atomic()
def inlinequery(bot, update):
    """Handle the inline query."""
    query = update.inline_query.query

    results = []
    for group in Group.select().where(Group.user == update.effective_user.id):
        members = ' '.join(member.alias for member in group.members)
        results.append(InlineQueryResultArticle(
            id=group.id,
            title=group.name,
            input_message_content=InputTextMessageContent(
                f'{members}\n\n{query}')))

    update.inline_query.answer(results)


dispatcher.add_error_handler(error)
dispatcher.add_handler(InlineQueryHandler(inlinequery))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('create', create_group_start)],
    states={
        CREATE_GROUP: [MessageHandler(Filters.text, create_group_complete)]
    },
    fallbacks=[]))

dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('change', group_change)],
    states={
        GROUP_CHANGE: [CallbackQueryHandler(group_action, pattern='group.change.')],
        GROUP_ACTION: [CallbackQueryHandler(group_action_select, pattern='group.', pass_user_data=True)],
        GROUP_ADD_MEMBERS: [CommandHandler('done', group_add_members_done),
                            MessageHandler(Filters.text, group_add_members, pass_user_data=True)],
    },
    fallbacks=[]))
