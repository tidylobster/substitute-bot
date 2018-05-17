# coding: utf-8
import re
from collections import namedtuple
from uuid import uuid4
from transliterate import translit
from telegram import InlineQueryResultArticle, InputTextMessageContent

from .models import database, Group, GroupUsers

Substitution = namedtuple('Substitution', 'end group_id')


# Internal functions
# ------------------

def _substitute(message, groups, draft=False):
    shift, msg = 0, message[:]
    for sub in groups:
        group = Group.get_by_id(sub.group_id)
        new_message = '( ... )' if draft else f'({", ".join("@" + member.alias for member in group.members)})'
        msg[sub.end+shift+1:sub.end+shift+2] = new_message
        shift += len(new_message)
    return msg


# Inline Query
# ------------

@database.atomic()
def substitute_query(bot, update):
    results = []
    query = update.inline_query.query

    if query:
        substitutions = []
        user_groups = Group.select().where(Group.user_id == update.effective_user.id)
        translitted = translit(query, 'ru', reversed=True)
        for group in user_groups:
            groups = re.findall(group.name, translitted, re.MULTILINE)
            substitutions.extend(Substitution(item.end, group.id) for item in groups)

        results.append(InlineQueryResultArticle(
            id=uuid4(),
            title="Automatic",
            input_message_content=InputTextMessageContent(_substitute(query, substitutions)),
            description=_substitute(query, substitutions, draft=True)))

    for group in Group.select().where(Group.user == update.effective_user.id):
        members = ' '.join(member.alias for member in group.members)
        results.append(InlineQueryResultArticle(
            id=group.id,
            title=f'@{group.name}',
            input_message_content=InputTextMessageContent(
                f'{members}\n{query}'),
            description=f'{members}\n{query}'))

    if not results and query:
        results.append(InlineQueryResultArticle(
            id=uuid4(),
            title="You don't have any existing group yet.",
            input_message_content=InputTextMessageContent(query),
            description=query))
    update.inline_query.answer(results)
