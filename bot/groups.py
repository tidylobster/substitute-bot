# coding: utf-8
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from peewee import IntegrityError
from .models import database, Group, GroupUsers

CREATE_GROUP, GROUP_CHANGE, GROUP_ACTION, GROUP_ADD_MEMBERS, GROUP_MEMBER_REMOVE = range(5)


def _validate_alias(alias):
    if len(alias.split(' ')) > 1:
        return False, 'Multiple usernames sent all at once. Try to send them one by one.'
    if len(re.findall('@', alias)) > 1:
        return False, 'Too many @ symbols.'
    if '@' in alias and not alias.startswith('@'):
        return False, 'Username should start with @.'
    if not 4 < len(alias) < 33 or '@' in alias and not 5 < len(alias) < 34:
        return False, 'Length of the username must be 5-32 symbols.'
    if len(re.findall('[^@a-zA-Z\d]+', alias)):
        return False, 'Invalid symbols in the username.'
    return True, None


def _build_action_menu(group):
    keyboard = [
        [InlineKeyboardButton('Add members', callback_data=f'group.add.{group.id}'),
         InlineKeyboardButton('Remove members', callback_data=f'group.remove.{group.id}')],
        [InlineKeyboardButton('Rename group', callback_data=f'group.rename.{group.id}'),
         InlineKeyboardButton('Delete group', callback_data=f'group.delete.{group.id}')]]

    message = f'Choose an action for @{group.name} group.\n\nMembers:'
    for member in group.members:
        message = f'{message}\n{member.alias}'
    return message, keyboard


def _build_members_menu(group):
    keyboard = []
    for index, member in enumerate(group.members):
        if index % 2 == 0:
            keyboard.append([InlineKeyboardButton(member.alias, callback_data=f'group.member.remove.{member.id}')])
        else:
            keyboard[-1].append(InlineKeyboardButton(member.alias, callback_data=f'group.member.remove.{member.id}'))
    else:
        keyboard.append([InlineKeyboardButton('← Back', callback_data='group.member.exit')])
    return None, keyboard


@database.atomic()
def create_group_start(bot, update):
    # Checking, that user has not exceeded the limit.
    groups = Group.select().where(Group.user == update.effective_message.from_user.id)
    if len(groups) > 10:
        update.effective_message.reply_text('You cannot have more that 10 groups.')
        return ConversationHandler.END

    update.effective_message.reply_text('Ok, send the name of the group /cancel')
    return CREATE_GROUP


@database.atomic()
def create_group_complete(bot, update):
    # Check, if group name has more tha 32 letters
    validated, message = _validate_alias(update.effective_message.text)

    if not validated:
        update.effective_message.reply_text(f'Sorry, invalid alias. {message}')
        return CREATE_GROUP

    try:
        Group.create(
            user=update.effective_message.from_user.id,
            name=update.effective_message.text)
        update.effective_message.reply_text('Saved.')
    except IntegrityError:  # Index fell down
        update.effective_message.reply_text('You have already created a group with that name.')
    finally:
        return ConversationHandler.END


@database.atomic()
def group_change(bot, update):
    keyboard = []
    for group in Group.select().where(Group.user == update.effective_message.from_user.id):
        keyboard.append([InlineKeyboardButton(
            text=f'@{group.name} | {len(group.members)} member(s)',
            callback_data=f'group.change.{group.id}'
        )])

    if not keyboard:
        update.effective_message.reply_text("You don't have any created groups yet. "
                                            "Use /create command to create a group.")
        return ConversationHandler.END

    update.effective_message.reply_text('Choose the group', reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_CHANGE


@database.atomic()
def group_action(bot, update):
    data = update.callback_query.data.split('.')
    message, keyboard = _build_action_menu(Group.get_by_id(data[-1]))
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_ACTION


def group_action_select(bot, update, user_data):
    update.callback_query.answer()
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    action = update.callback_query.data.split('.')[-2]  # specifies, which action has to be performed

    if action == 'add':
        update.effective_message.reply_text(
            f'Ok, send usernames (like @{update.effective_user.username}) one by one. '
            f'When you will be ready, send /done for completing.')
        return GROUP_ADD_MEMBERS

    if action == 'remove':
        return group_member_remove(bot, update, user_data)

    if action == 'rename':
        pass
    if action == 'delete':
        pass

    update.effective_message.reply_text('Fuck yourself')
    return ConversationHandler.END  # should never hit this..


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
def group_add_members_done(bot, update, user_data):
    update.effective_message.reply_text('Saved new members.')

    message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_ACTION


@database.atomic()
def group_member_remove(bot, update, user_data):
    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    if len(keyboard) == 1:
        update.callback_query.answer("There isn't any member in this group.")
        return GROUP_ACTION
    update.effective_message.edit_text('Choose members to remove.', reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_MEMBER_REMOVE


@database.atomic()
def group_member_remove_complete(bot, update, user_data):
    member_id = update.callback_query.data.split('.')[-1]
    GroupUsers.delete().where(GroupUsers.id == member_id).execute()
    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    if len(keyboard) == 1:
        message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
        update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_MEMBER_REMOVE


@database.atomic()
def group_member_exit(bot, update, user_data):
    message, keyboard = _build_action_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_ACTION