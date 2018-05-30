# coding: utf-8
import datetime
from uuid import uuid4

from telegram import ParseMode
from transliterate.exceptions import LanguageDetectionError
from telegram import InlineQueryResultArticle, InputTextMessageContent
from pyrogram.api import functions

from .updater import config
from .substitutegroup import *
from .models import database, Group
from .utils import client_wrapper


# Inline Query
# ------------

@database.atomic()
def inline_mode(bot, update):
    results, auto_triggered = [], False
    query = update.inline_query.query

    if query:
        auto_triggered = True  # Automatic substitution was triggered
        groups = Group.select().where(Group.chat == update.effective_user.id)
        results.append(InlineQueryResultArticle(
            id=uuid4(),
            title="Auto",
            input_message_content=InputTextMessageContent(substitute_groups(query, groups), parse_mode=ParseMode.MARKDOWN),
            description=substitute_groups(query, groups, draft=True)))

    for group in Group.select().where(Group.chat == update.effective_user.id).order_by(Group.usage.desc()):
        members = ' '.join(member.alias for member in group.members).strip() or 'Empty group'
        results.append(InlineQueryResultArticle(
            id=group.id,
            title=f'{group.name}',
            input_message_content=InputTextMessageContent(f'{query}\n\n{group_bold_text(group.name)} ({escape_markdown(members)})', parse_mode=ParseMode.MARKDOWN),
            description=f'{members}'))

    if not results and query or len(results) == 1 and auto_triggered:
        return update.inline_query.answer([], is_personal=True,
            switch_pm_text='Create own groups', switch_pm_parameter='start')

    update.inline_query.answer(results, is_personal=True)


@database.atomic()
def inline_chosen(bot, update):
    try:
        q = (Group
             .update({Group.usage: Group.usage + 1})
             .where(Group.id == int(update.chosen_inline_result.result_id)))
        q.execute()
    except ValueError:
        pass  # int() get uuid4 string -> do nothing


# Checking every message
# ----------------------

def check_every_message(bot, update):
    if update.effective_message.chat_id == update.effective_message.from_user.id:
        return None  # Don't check anything, if this is self-conversation

    user_groups = Group.select().where(Group.chat == update.effective_chat.id)
    try:
        translitted = translit(update.effective_message.text, reversed=True)
    except LanguageDetectionError:
        translitted = update.effective_message.text

    mentioned = []
    for group in user_groups:
        if group.name in translitted.lower() and group.id not in mentioned:
            mentioned.append(group.id)
            if group.members:
                update.effective_message.reply_text(f"Guys {get_group_members_string(group)}, you have been mentioned.", parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text(f"A group {group_bold_text(group.name)} was mentioned, but there are no members in it.", parse_mode=ParseMode.MARKDOWN)


@client_wrapper
@database.atomic()
def mention_all(bot, update, app, chat_data):
    """ Mentioning all members in the chat """
    if not update.effective_chat.type == 'group':
        return update.effective_message.reply_text('Sorry, I only work with groups, not supergroups or channels.', quote=False)
    if chat_data.get('last_call'):
        minutes = config('GROUP_MENTION_ALL_TIME', cast=int)
        if datetime.datetime.now() - chat_data.get('last_call') < datetime.timedelta(minutes=minutes):
            difference = datetime.timedelta(minutes=minutes) - (datetime.datetime.now() - chat_data.get('last_call'))
            return update.effective_message.reply_text(
                f"/all can be called again in {int(difference.total_seconds())} seconds.", quote=False)

    full_chat = app.send(functions.messages.GetFullChat(chat_id=app.resolve_peer(update.effective_chat.id).chat_id))

    messsage = ''
    members, limit = [], config('GROUP_MENTION_ALL_LIMIT', cast=int)
    for user in full_chat.users:
        if limit == 0:
            messsage = f"Sorry, I am restricted to show only up to " \
                       f"{config('GROUP_MENTION_ALL_LIMIT', cast=int)} members in the group."
            break
        if user.bot:
            continue

        members.append(f'@{user.username}')
        limit -= 1

    chat_data.update({'last_call': datetime.datetime.now()})
    update.effective_message.reply_text(' '.join(members), quote=False)
    if messsage:
        update.effective_message.reply_text(messsage, quote=False)
