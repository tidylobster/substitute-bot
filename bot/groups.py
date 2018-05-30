# coding: utf-8
import re
from decouple import Config, RepositoryEnv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler
from telegram.utils.helpers import escape_markdown
from peewee import IntegrityError

from .models import database, Group, GroupUsers
from .substitutegroup import group_bold_text, get_translitted

CREATE_GROUP, GROUP_ADD_MEMBERS, GROUP_REMOVE_MEMBERS, GROUP_RENAME, GROUP_DELETE = range(5)
config = Config(RepositoryEnv('config.env'))

# Internal functions
# ------------------


def _construct_alphabet():
    return 'ՏyIэԵПЕΜეцхլвaeբPчαზΛbнTбՑзлОწыრვДSdიԼZβρMիХჯლЧСბжֆGъоаγKфთWVђՅNuաԿτΞզкшЦlπУЋгΚҐჰgQნФքօუFґԽկΖსყЫ' \
           'խsЖΡΥXБგрνკԻkМЗեյԴտEჟԶjYλziеՆЈրΕсՍεκЬՄЪHoOЭІოხհΠգpBАՎფδНΣՖΦпմИმΒაfცrվйтtդԱьШΔοպՐιіΤwUԳКζxүდპDս' \
           'ћυLиЙμΑЂქΝԲՀВևqφЛhΟσмТնցՊCRјҮՔРJcξՕΙnΓдГvmуტA'


def _validate_alias(alias, use_at=True, use_alphabet=False):
    if len(alias.split(' ')) > 1:
        return False, 'Multiple usernames sent all at once. Try to send them one by one.'
    if use_at and len(re.findall('@', alias)) > 1:
        return False, 'Too many @ symbols.'
    if use_at and '@' in alias and not alias.startswith('@'):
        return False, 'Username should start with @.'
    if not 4 < len(alias) < 33 or use_at and '@' in alias and not 5 < len(alias) < 34:
        return False, 'Length of the username must be 5-32 symbols.'

    alphabet = _construct_alphabet() if use_alphabet else ''
    symbols = '@_' if use_at else '_'
    if len(re.findall(f'[^{symbols}a-zA-Z{alphabet}\d]+', alias)):
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


def _build_action_menu(group, update):
    keyboard = []
    if group.user == update.effective_user.id:  # if creator
        message = f'Choose an action for {group_bold_text(group.name)} group.'
        keyboard.extend([[InlineKeyboardButton('Add members', callback_data=f'group.add.{group.id}'),
                          InlineKeyboardButton('Remove members', callback_data=f'group.remove.{group.id}')],
                         [InlineKeyboardButton('Rename group', callback_data=f'group.rename.{group.id}'),
                          InlineKeyboardButton('Delete group', callback_data=f'group.delete.{group.id}')]])
    else:
        message = f'The {group_bold_text(group.name)} group.'

    if GroupUsers.select().where((GroupUsers.group == group) & (GroupUsers.alias == update.effective_user.name)).first():
        keyboard.extend([[InlineKeyboardButton('← Back', callback_data=f'group.exit'),
                          InlineKeyboardButton('Leave group', callback_data=f'group.leave.{group.id}')]])
    else:
        keyboard.extend([[InlineKeyboardButton('← Back', callback_data=f'group.exit'),
                          InlineKeyboardButton('Join group', callback_data=f'group.join.{group.id}')]])

    if group.members:
        message = f'{message}\n\nMembers:'
        for member in group.members:
            message = f'{message}\n- {member.alias[1:]}'
    else:
        message = f'{message}\n\n No members yet.'

    return {
        'text': message,
        'reply_markup': InlineKeyboardMarkup(keyboard),
        'parse_mode': ParseMode.MARKDOWN}


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
    if len(groups) > config('GROUP_LIMIT', cast=int):
        update.effective_message.reply_text(f'You cannot have more that {config("GROUP_LIMIT", cast=int)} groups.')
        return ConversationHandler.END

    update.effective_message.reply_text('Ok, send the name of the group. /cancel')
    return CREATE_GROUP


@database.atomic()
def group_create_complete(bot, update):
    # Check, if group name has more tha 32 letters
    validated, message = _validate_alias(update.effective_message.text, use_at=False, use_alphabet=True)

    if not validated:
        update.effective_message.reply_text(f'Sorry, invalid alias. {message}')
        return CREATE_GROUP

    try:
        group_name = get_translitted(update.effective_message.text, case_insansitive=True)
        group = Group.create(
            user=update.effective_message.from_user.id,
            chat=update.effective_message.chat_id,
            name=group_name)
        GroupUsers.create(group=group, alias=update.effective_user.name)
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
    kwargs = _build_action_menu(Group.get_by_id(user_data.get('effective_group')), update)
    update.effective_message.edit_text(**kwargs)


@database.atomic()
def group_exit(bot, update):
    message, keyboard = _build_group_menu(update.effective_chat.id)
    update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


# Adding members
# --------------

@database.atomic()
def group_join(bot, update):
    try:
        group = Group.get_by_id(int(update.callback_query.data.split('.')[-1]))
        if len(group.members) >= config("GROUP_MEMBERS_LIMIT", cast=int):
            return update.callback_query.answer("Maximum amount of members in the group.")
        GroupUsers.create(group=group, alias=update.callback_query.from_user.name)

        kwargs = _build_action_menu(group, update)
        update.effective_message.edit_text(**kwargs)
        update.effective_message.reply_text(
            f"{update.callback_query.from_user.name} joined the group {group_bold_text(group.name)}", quote=False, parse_mode=ParseMode.MARKDOWN)
    except IntegrityError:
        update.callback_query.answer("You're already in that group.")


@database.atomic()
def group_leave(bot, update):
    group = Group.get_by_id(int(update.callback_query.data.split('.')[-1]))
    GroupUsers.delete().where(
        (GroupUsers.group == group) & (GroupUsers.alias == update.callback_query.from_user.name)
    ).execute()

    kwargs = _build_action_menu(group, update)
    update.effective_message.edit_text(**kwargs)
    update.effective_message.reply_text(
        f"{update.callback_query.from_user.name} left the group {group_bold_text(group.name)}", quote=False, parse_mode=ParseMode.MARKDOWN)


@database.atomic()
def group_add_members_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    group = Group.get_by_id(user_data.get('effective_group'))
    if group.user != update.callback_query.from_user.id:
        update.callback_query.answer('You are not allowed to add new members.')
        return ConversationHandler.END
    if len(group.members) >= config('GROUP_MEMBERS_LIMIT', cast=int):
        update.callback_query.answer(f'You can only have up to {config("GROUP_MEMBERS_LIMIT", cast=int)} users in the group.')
        return ConversationHandler.END

    update.callback_query.answer()
    update.effective_message.reply_text(
        f'Ok, send usernames (like {update.effective_user.name}) one by one. '
        f'When you will be ready, send /done for completing.')
    return GROUP_ADD_MEMBERS


@database.atomic()
def group_add_members(bot, update, user_data):
    group = Group.get_by_id(user_data.get('effective_group'))
    try:
        alias = update.effective_message.text
        validated, message = _validate_alias(alias, use_at=True)
        if not validated:
            update.effective_message.reply_text(f'Sorry, invalid alias. {message}')
        else:
            alias = alias if '@' in alias else f'@{alias}'
            GroupUsers.create(group=group, alias=alias)
            update.effective_message.reply_text(f'Added `{escape_markdown(alias)}`', parse_mode=ParseMode.MARKDOWN)
            if len(group.members) >= config('GROUP_MEMBERS_LIMIT', cast=int):
                kwargs = _build_action_menu(group, update)
                update.effective_message.reply_text(f'Maximum amount of members reached.')
                update.effective_message.reply_text(**kwargs)
                return ConversationHandler.END

    except IntegrityError:
        update.effective_message.reply_text(
            f'You have already added `{escape_markdown(alias)}` to the group',
            parse_mode=ParseMode.MARKDOWN)

    return GROUP_ADD_MEMBERS


@database.atomic()
def group_add_members_complete(bot, update, user_data):
    update.effective_message.reply_text('Saved new members.')

    kwargs = _build_action_menu(Group.get_by_id(user_data.get('effective_group')), update)
    update.effective_message.reply_text(**kwargs)
    return ConversationHandler.END


# Removing members
# ----------------

@database.atomic()
def group_remove_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    group = Group.get_by_id(user_data.get('effective_group'))
    if group.user != update.callback_query.from_user.id:
        update.callback_query.answer('You are not allowed to remove members.')
        return ConversationHandler.END
    if not group.members:
        update.callback_query.answer("There aren't any members in the group.")
        return ConversationHandler.END

    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    update.effective_message.edit_text('Choose members to remove.', reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_REMOVE_MEMBERS


@database.atomic()
def group_remove_members(bot, update, user_data):
    member_id = update.callback_query.data.split('.')[-1]
    GroupUsers.delete().where(GroupUsers.id == member_id).execute()
    _, keyboard = _build_members_menu(Group.get_by_id(user_data.get('effective_group')))
    if len(keyboard) == 1:
        kwargs = _build_action_menu(Group.get_by_id(user_data.get('effective_group')), update)
        update.effective_message.edit_text(**kwargs)
    else:
        update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    return GROUP_REMOVE_MEMBERS


@database.atomic()
def group_remove_exit(bot, update, user_data):
    kwargs = _build_action_menu(Group.get_by_id(user_data.get('effective_group')), update)
    update.effective_message.edit_text(**kwargs)
    return ConversationHandler.END


# Renaming group
# --------------

def group_rename_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    group = Group.get_by_id(user_data.get('effective_group'))
    if group.user != update.callback_query.from_user.id:
        update.callback_query.answer('You are not allowed to rename the group.')
        return ConversationHandler.END

    update.callback_query.answer()
    update.effective_message.reply_text('Send the new name of the group.')
    return GROUP_RENAME


@database.atomic()
def group_rename_complete(bot, update, user_data):
    validated, message = _validate_alias(update.effective_message.text, use_at=False, use_alphabet=True)
    if not validated:
        update.effective_message.reply_text(f'Sorry, invalid group name. {message}')
        return GROUP_RENAME

    group = Group.get_by_id(user_data.get('effective_group'))
    try:
        group.name = get_translitted(update.effective_message.text, case_insansitive=True)
        group.save()
        update.effective_message.reply_text('Saved.')
    except IntegrityError:
        update.effective_message.reply_text("You've already created a group with that name. Try again or /cancel")
        return GROUP_RENAME

    kwargs = _build_action_menu(group, update)
    update.effective_message.reply_text(**kwargs)
    return ConversationHandler.END


# Deleting group
# --------------

@database.atomic()
def group_delete_enter(bot, update, user_data):
    user_data['effective_group'] = int(update.callback_query.data.split('.')[-1])
    group = Group.get_by_id(user_data.get('effective_group'))
    if group.user != update.callback_query.from_user.id:
        update.callback_query.answer('You are not allowed to delete the group.')
        return ConversationHandler.END

    update.effective_message.edit_text(
        text=f'Are you sure, you want to delete the group {group_bold_text(group.name)}?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Yes', callback_data='group.delete.yes'),
             InlineKeyboardButton('No', callback_data='group.delete.no')]]),
        parse_mode=ParseMode.MARKDOWN)
    return GROUP_DELETE


@database.atomic()
def group_delete_complete(bot, update, user_data):
    group = Group.get_by_id(user_data.get('effective_group'))
    action = update.callback_query.data.split('.')[-1]

    if action == 'yes':
        group.delete_instance(recursive=True)
        update.callback_query.answer('Group have been deleted')
        message, keyboard = _build_group_menu(update.effective_chat.id)
        update.effective_message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    if action == 'no':
        kwargs = _build_action_menu(group, update)
        update.effective_message.edit_text(**kwargs)

    return ConversationHandler.END
