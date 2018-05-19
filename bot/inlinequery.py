# coding: utf-8
import re
from collections import namedtuple
from uuid import uuid4
from transliterate import translit
from telegram import InlineQueryResultArticle, InputTextMessageContent

from .models import database, Group, GroupUsers

Substitution = namedtuple('Substitution', 'id name start end ')


# Internal functions
# ------------------

def _substitute(message, groups, draft=False):
    shift, new_msg = -1, message[:]
    for sub in groups:
        group = Group.get_by_id(sub.id)
        replacements = '( ... )' if draft else f'{" ".join(member.alias for member in group.members)}'
        new_msg = f'{new_msg[:sub.start+shift]}{replacements}{new_msg[sub.end + shift:]}'
        shift += len(replacements) - len(sub.name)
    return new_msg


# Inline Query
# ------------

@database.atomic()
def inline_mode(bot, update):
    results = []
    query = update.inline_query.query

    if query:
        substitutions = []
        user_groups = Group.select().where(Group.user == update.effective_user.id)
        translitted = translit(query, 'ru', reversed=True)
        for group in user_groups:
            groups = re.finditer(f'@?{group.name}', translitted, re.MULTILINE)
            substitutions.extend(Substitution(group.id, group.name, item.start(0), item.end(0)) for item in groups)

        if substitutions:
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="Auto",
                input_message_content=InputTextMessageContent(_substitute(query, substitutions)),
                description=_substitute(query, substitutions, draft=True)))

    for group in Group.select().where(Group.user == update.effective_user.id):
        members = ' '.join(member.alias for member in group.members)
        results.append(InlineQueryResultArticle(
            id=group.id,
            title=f'{group.name}',
            input_message_content=InputTextMessageContent(
                f'{query}\n{members}'),
            description=f'{members}'))

    if not results and query:
        results.append(InlineQueryResultArticle(
            id=uuid4(),
            title="You don't have any existing group yet.",
            input_message_content=InputTextMessageContent(query),
            description=query))
    update.inline_query.answer(results)
