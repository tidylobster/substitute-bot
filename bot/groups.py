# coding: utf-8
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from peewee import IntegrityError
from .models import database, Group, GroupUsers

CREATE_GROUP, GROUP_CHANGE, GROUP_ACTION, GROUP_ADD_MEMBERS = range(4)


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
    # Check, if group name has more tha 16 letters
    if len(update.effective_message.text) > 16:
        update.effective_message.reply_text(
            'You can only create groups that have 16 symbols in their names. Try again or /cancel')
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

    group = Group.get_by_id(data[-1])
    keyboard = [
        [InlineKeyboardButton('Add members', callback_data=f'group.add.{group.id}'),
         InlineKeyboardButton('Remove members', callback_data=f'group.remove.{group.id}')],
        [InlineKeyboardButton('Rename group', callback_data=f'group.rename.{group.id}'),
         InlineKeyboardButton('Delete group', callback_data=f'group.delete.{group.id}')]]

    message = f'Choose action for @{group.name}\n'
    for member in group.members:
        message = f'{message}\n{member.alias}'
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
        pass
    if action == 'rename':
        pass
    if action == 'delete':
        pass

    update.effective_message.reply_text('Fuck yourself')
    return ConversationHandler.END  # should never hit this..


def group_add_members(bot, update, user_data):
    group = Group.get_by_id(user_data.get('effective_group'))
    try:
        GroupUsers.create(group=group, alias=update.effective_message.text)
    except IntegrityError:
        update.effective_message.reply_text(f'You already added {update.effective_message.text} to the group')
    finally:
        return GROUP_ADD_MEMBERS


def group_add_members_done(bot, update):
    update.effective_message.reply_text('Saved new members.')
    return ConversationHandler.END