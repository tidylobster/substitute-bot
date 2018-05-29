# coding: utf-8
from uuid import uuid4

from telegram import ParseMode
from transliterate.exceptions import LanguageDetectionError
from telegram import InlineQueryResultArticle, InputTextMessageContent

from .substitutegroup import *
from .models import database, Group


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
            input_message_content=InputTextMessageContent(f'{query}\n\n{escape_markdown(members)}', parse_mode=ParseMode.MARKDOWN),
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
        if clear_group_name(group.name) in translitted.lower() and group.id not in mentioned:
            mentioned.append(group.id)
            edited_group_name = group_bold_text(group.name)
            if group.members:
                update.effective_message.reply_text(f"Guys {get_group_members_string(group)}, you have been mentioned.", parse_mode=ParseMode.MARKDOWN)
            else:
                update.effective_message.reply_text(f"A group {edited_group_name} was mentioned, but there are no members in it.", parse_mode=ParseMode.MARKDOWN)
