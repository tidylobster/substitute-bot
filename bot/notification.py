# coding: utf-8
import re
from collections import namedtuple
from uuid import uuid4

from telegram import ParseMode
from transliterate import translit
from transliterate.exceptions import LanguageDetectionError
from telegram import InlineQueryResultArticle, InputTextMessageContent

from .substitutegroup import substitute_groups, group_bold_text
from .models import database, Group, GroupUsers

Substitution = namedtuple('Substitution', 'id name index')


# Inline Query
# ------------

@database.atomic()
def inline_mode(bot, update):
    results = []
    query = update.inline_query.query

    if query:
        # Automatic substitution
        try:
            groups = Group.select().where(Group.chat == update.effective_user.id)

            results.append(InlineQueryResultArticle(id=uuid4(), title="Auto",
                input_message_content=InputTextMessageContent(substitute_groups(query, groups),parse_mode=ParseMode.MARKDOWN),
                description=substitute_groups(query, groups, draft=True)))
        except LanguageDetectionError:
            pass

    for group in Group.select().where(Group.chat == update.effective_user.id):
        members = ' '.join(member.alias for member in group.members).strip() or 'Empty group'
        results.append(InlineQueryResultArticle(id=group.id, title=f'{group.name}',
            input_message_content=InputTextMessageContent(f'{query}\n\n{members}', parse_mode=ParseMode.MARKDOWN), description=f'{members}'))

    if not results and query:
        return update.inline_query.answer([], is_personal=True,
            switch_pm_text='Create own groups', switch_pm_parameter='start')

    update.inline_query.answer(results, is_personal=True)


# Checking every message
# ----------------------

def check_every_message(bot, update):
    if update.effective_message.chat_id == update.effective_message.from_user.id:
        return None  # Don't check anything, if this is self-conversation

    user_groups = Group.select().where(Group.chat == update.effective_chat.id)
    translitted = translit(update.effective_message.text, 'ru', reversed=True)
    for group in user_groups:
        if group.name[1:].lower() in translitted.lower():
            edited_group_name = group_bold_text(group.name)
            if group.members:
                members = ' '.join(member.alias for member in group.members)
                update.effective_message.reply_text(f"Guys {edited_group_name} ({members}), you have been mentioned.")
            else:
                update.effective_message.reply_text(f"A group {edited_group_name} was mentioned, but there are no members in it.")
