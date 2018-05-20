# coding: utf-8
import re
import os
import string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from transliterate import translit
from transliterate.contrib import languages
from peewee import IntegrityError
from .models import database, Group, GroupUsers

CREATE_GROUP, GROUP_ADD_MEMBERS, GROUP_REMOVE_MEMBERS, GROUP_RENAME, GROUP_DELETE = range(5)


# Internal functions
# ------------------


def _construct_alphabet():
    return 'ՏyIэԵПЕΜეцхլвaeբPчαზΛbнTбՑзлОწыრვДSdიԼZβρMիХჯლЧСბжֆGъоаγKфთWVђՅNuաԿτΞզкшЦlπУЋгΚҐჰgQნФքօუFґԽկΖსყЫ' \
           'խsЖΡΥXБგрνკԻkМЗեյԴտEჟԶjYλziеՆЈրΕсՍεκЬՄЪHoOЭІოხհΠգpBАՎფδНΣՖΦпմИმΒაfცrվйтtդԱьШΔοպՐιіΤwUԳКζxүდპDս' \
           'ћυLиЙμΑЂქΝԲՀВևqφЛhΟσмТնցՊCRјҮՔРJcξՕΙnΓдГvmуტA'


def _construct_group_name(group_name):
    group_name = f'@{group_name}' if not group_name.startswith('@') else group_name
    alphabet = string.ascii_letters + string.digits + '@_'
    if not all(map(lambda x: x in alphabet, group_name)):
        group_name = translit(group_name, reversed=True)
    return group_name


def _validate_alias(alias, use_alphabet=False):
    if len(alias.split(' ')) > 1:
        return False, 'Multiple usernames sent all at once. Try to send them one by one.'
    if len(re.findall('@', alias)) > 1:
        return False, 'Too many @ symbols.'
    if '@' in alias and not alias.startswith('@'):
        return False, 'Username should start with @.'
    if not 4 < len(alias) < 33 or '@' in alias and not 5 < len(alias) < 34:
        return False, 'Length of the username must be 5-32 symbols.'

    alphabet = _construct_alphabet() if use_alphabet else ''
    if len(re.findall(f'[^@_a-zA-Z{alphabet}\d]+', alias)):
        return False, 'Invalid symbols in the username.'
    return True, None


def _build_group_menu(chat_id):
    keyboard = []
    for group in Group.select().where(Group.chat == chat_id):
        keyboard.append([InlineKeyboardButton(
            text=f'{group.name} | {len(group.members)} member(s)',
            callback_data=f'group.list.{group.id}'
        )])
    if not keyboard:
        return "You don't have any created groups yet. Use /create command to create a group.", keyboard
    return 'Choose the group', keyboard


def _build_action_menu(group):
    keyboard = [
        [InlineKeyboardButton('Add members', callback_data=f'group.add.{group.id}'),
         InlineKeyboardButton('Remove members', callback_data=f'group.remove.{group.id}')],
        [InlineKeyboardButton('Rename group', callback_data=f'group.rename.{group.id}'),
         InlineKeyboardButton('Delete group', callback_data=f'group.delete.{group.id}')],
        [InlineKeyboardButton('← Back', callback_data=f'group.exit')]]

    message = f'Choose an action for {group.name} group.'
    if group.members:
        message = f'{message}\n\nMembers:'
        for member in group.members:
            message = f'{message}\n{member.alias}'
    return message, keyboard


def _build_members_menu(group):
    keyboard = []
    for index, member in enumerate(group.members):
        if index % 2 == 0:
            keyboard.append([InlineKeyboardButton(member.alias, callback_data=f'group.remove.member.{member.id}')])
        else:
            keyboard[-1].append(InlineKeyboardButton(member.alias, callback_data=f'group.remove.member.{member.id}'))
    else:
        keyboard.append([InlineKeyboardButton('← Back', callback_data='group.remove.exit')])
    return None, keyboard


# /create command
# ---------------

@database.atomic()
def group_create(bot, update):
    # Checking, that user/chat has not exceeded the limit.
    groups = Group.select().where(Group.chat == update.effective_message.chat_id)
    if len(groups) > 10:
        update.effective_message.reply_text('You cannot have more that 10 groups.')
        return ConversationHandler.END

    update.effective_message.reply_text('Ok, send the name of the group. /cancel')
    return CREATE_GROUP


@database.atomic()
def group_create_complete(bot, update):
    # Check, if group name has more tha 32 letters
    validated, message = _validate_alias(update.effective_message.text, use_alphabet=True)

    if not validated:
        update.effective_message.reply_text(f'Sorry, invalid alias. {message}')
        return CREATE_GROUP

    try:
        group_name = _construct_group_name(update.effective_message.text)
        Group.create(
            user=update.effective_message.from_user.id,
            chat=update.effective_message.chat_id,
            name=group_name)
        update.effective_message.reply_text('Saved. You can see all of your /groups if you like.')
        return ConversationHandler.END
    except IntegrityError:  # Index fell down
        update.effective_message.reply_text('You have already created a group with that name.')
        return CREATE_GROUP


# /groups command
# ---------------

@database.atomic()
def group_list(bot, update):
    message, keyboard = _build_group_menu(update.effective_chat.id)
    update.effective_message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


@database.atomic()
def group_open(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


@database.atomic()
def group_exit(bot, update):
    message, keyboard = _build_group_menu(update.effective_chat.id)
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


# Adding members
# --------------

def group_add_members_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    update.callback_query.answer()
    update.effective_message.reply_text(
        f'Ok, send usernames (like @{update.effective_user.username}) one by one. '
        f'When you will be ready, send /done for completing.')
    return GROUP_ADD_MEMBERS


@database.atomic()
def group_add_members(bot, update, user_data):
    group = Group.get_by_id(user_data.get('effective_group'))
    try:
        alias = update.effective_message.text
        validated, message = _validate_alias(alias)
        if not validated:
            update.effective_message.reply_text(f'Sorry, invalid alias. {message}')
        else:
            alias = alias if '@' in alias else f'@{alias}'
            GroupUsers.create(group=group, alias=alias)
            update.effective_message.reply_text(f'Added {alias}')
    except IntegrityError:
        update.effective_message.reply_text(f'You already added {update.effective_message.text} to the group')
    finally:
        return GROUP_ADD_MEMBERS


@database.atomic()
def group_add_members_complete(bot, update, user_data):
    update.effective_message.reply_text('Saved new members.')

    message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# Removing members
# ----------------

@database.atomic()
def group_remove_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    if len(keyboard) == 1:
        update.callback_query.answer("There isn't any member in this group.")
        return ConversationHandler.END
    update.effective_message.edit_text('Choose members to remove.', reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_REMOVE_MEMBERS


@database.atomic()
def group_remove_members(bot, update, user_data):
    member_id = update.callback_query.data.split('.')[-1]
    GroupUsers.delete().where(GroupUsers.id == member_id).execute()
    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    if len(keyboard) == 1:
        message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
        update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_REMOVE_MEMBERS


@database.atomic()
def group_remove_exit(bot, update, user_data):
    message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# Renaming group
# --------------

def group_rename_enter(bot, update, user_data):
    update.callback_query.answer()
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    update.effective_message.reply_text('Send the new name of the group.')
    return GROUP_RENAME


@database.atomic()
def group_rename_complete(bot, update, user_data):
    validated, message = _validate_alias(update.effective_message.text, use_alphabet=True)
    if not validated:
        update.effective_message.reply_text(f'Sorry, invalid group. {message}')
        return GROUP_RENAME

    group = Group.get_by_id(user_data.get('effective_group'))
    try:
        group.name = _construct_group_name(update.effective_message.text)
        group.save()
        update.effective_message.reply_text('Saved.')
    except IntegrityError:
        update.effective_message.reply_text("You've already created a group with that name. Try again or /cancel")
        return GROUP_RENAME

    message, keyboard = _build_action_menu(group)
    update.effective_message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# Deleting group
# --------------

@database.atomic()
def group_delete_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    group = Group.get_by_id(user_data.get('effective_group'))
    update.effective_message.edit_text(
        text=f'Are you sure, you want to delete the group {group.name}?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Yes', callback_data='group.delete.yes'),
             InlineKeyboardButton('No', callback_data='group.delete.no')]
        ]))
    return GROUP_DELETE


@database.atomic()
def group_delete_complete(bot, update, user_data):
    group = Group.get_by_id(user_data.get('effective_group'))
    action = update.callback_query.data.split('.')[-1]

    if action == 'yes':
        group.delete_instance()
        update.callback_query.answer('Group have been deleted')
        message, keyboard = _build_group_menu(update.effective_chat.id)
        update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    if action == 'no':
        message, keyboard = _build_action_menu(group)
        update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    return ConversationHandler.END
