import pytest
from random import choice
from string import ascii_lowercase, digits
from tgintegration import BotIntegrationClient
from decouple import Config, RepositoryEnv


config = Config(RepositoryEnv('config.env'))

@pytest.fixture(scope="session")
def client():
    integration_client = BotIntegrationClient(
        bot_under_test=config('BOT_NAME'),
        session_name='test_account',
        api_id=config('API_ID'),
        api_hash=config('API_HASH'),
        max_wait_response=20,
        min_wait_consecutive=20,
        global_action_delay=3)

    integration_client.start()
    integration_client.send_command(command='/cancel', bot=config('BOT_NAME'))

    try: 
        yield integration_client
    except Exception: 
        integration_client.send_command(command='/cancel', bot=config('BOT_NAME'))
    integration_client.stop()


# Tests
# -----

def test_start(client: BotIntegrationClient):
    client.send_message(text="test_start", chat_id=config('BOT_NAME'))

    response = client.send_command_await("/start", num_expected=1)
    assert response.num_messages == 1
    assert response.full_text.startswith("Hello")


def test_create_group_abort(client: BotIntegrationClient):
    client.send_message(text="test_create_group_abort", chat_id=config('BOT_NAME'))

    response = client.send_command_await("/create", num_expected=1)
    assert response.num_messages == 1
    assert response.full_text.startswith("Ok, send the name of the group")

    response = client.send_command_await("/cancel", num_expected=1)
    assert response.num_messages == 1
    assert response.full_text.startswith("Sure, what now?")


def test_create_group_with_valid_symbols(client: BotIntegrationClient):
    client.send_message(text="test_create_group_with_valid_symbols", chat_id=config('BOT_NAME'))

    group_name = create_group_command(client)
    assert group_is_existing(client, group_name), "Cannot find created group in the list"


def test_rename_existing_group(client: BotIntegrationClient):
    client.send_message(text="test_rename_existing_group", chat_id=config('BOT_NAME'))

    group_name = create_group_command(client)
    menu = enter_group(client, group_name)
    rename_group_command(client, menu)
    

def test_delete_existing_group(client: BotIntegrationClient):
    client.send_message(text="test_delete_existing_group", chat_id=config('BOT_NAME'))

    group_name = create_group_command(client)
    menu = enter_group(client, group_name)
    delete_group_command(client, group_name, menu)


def test_integration_create_rename_delete_group(client: BotIntegrationClient):
    client.send_message(text="test_integration_create_rename_delete_group", chat_id=config('BOT_NAME'))
    
    group_name = create_group_command(client)
    menu = enter_group(client, group_name)
    new_name = rename_group_command(client, menu)
    delete_group_command(client, new_name, menu)


def test_add_members_to_existing_group(client: BotIntegrationClient):
    client.send_message(text="test_add_members_to_existing_group", chat_id=config('BOT_NAME'))

    group_name = create_group_command(client)
    group_name = enter_group(client, group_name)
    button = group_name.inline_keyboards[0].press_button_await(
        pattern=r'.*Add members', min_wait_consecutive=5)

    assert not button.empty, 'Pressing "Add members" button had no effect.'
    assert button.full_text.startswith('Ok, send'), "Adding users' message has been changed."
    
    user_name = generate_name()
    response = client.send_message_await(user_name, num_expected=1)
    assert response.full_text.startswith("Added")

    response = client.send_command_await("/done", num_expected=2)
    assert response[0].text.startswith('Saved new members')
    
    members = response[1].text.split('\n')[3:]
    members = [item.split()[1] for item in members]
    assert user_name in members, "User hasn't been added"
    

# def test_remove_members_from_existing_group(client: BotIntegrationClient):
#     client.send_message(text="test_remove_members_from_existing_group", chat_id=config('BOT_NAME'))


# Support Functions
# -----------------

def generate_name(length=8, alphabet=None):
    if not alphabet:
        alphabet = ascii_lowercase + digits
    
    return ''.join([choice(alphabet) for _ in range(length)])


def create_group_command(client: BotIntegrationClient, generated_name: str = None):
    if not generated_name:
        generated_name = generate_name()

    client.send_command_await('/create', num_expected=1)
    response = client.send_message_await(generated_name)
    assert response.full_text.startswith('Saved'), \
        "Correctly saved responses start with 'Saved.'"
    
    return generated_name


def enter_group(client: BotIntegrationClient, name: str):
    response = client.send_command_await('/groups', num_expected=1)
    pattern = r'.*{} | .+ member(s)'.format(name)
    menu = response.inline_keyboards[0].press_button_await(pattern=pattern)
    
    assert not menu.empty, 'Pressing "group_name" button had no effect.'
    assert name.lower() in menu.full_text.lower()
    return menu


def rename_group_command(client: BotIntegrationClient, menu):
    new_name = generate_name()
    menu.inline_keyboards[0].press_button_await(
        pattern=r'.*Rename group', min_wait_consecutive=5)
    response = client.send_message_await(new_name, num_expected=2)

    assert response[0].text.startswith('Saved')
    assert response[1].text.startswith('Choose an action')
    assert group_is_existing(client, new_name)
    return new_name


def delete_group_command(client: BotIntegrationClient, name: str, menu):
    assert group_is_existing(client, name)

    delete_group = menu.inline_keyboards[0].press_button_await(
        pattern=r'.*Delete group', min_wait_consecutive=3)
    delete_group.inline_keyboards[0].press_button_await(
        pattern=r'.*Yes', min_wait_consecutive=3)

    assert not (group_is_existing(client, name))


def group_is_existing(client: BotIntegrationClient, group_name: str):
    response = client.send_command_await("/groups", num_expected=1)
    for row in response.inline_keyboards[0].rows:
        assert len(row) == 1, "Each row should be of length 1"
        if row[0].text.startswith(group_name):
            return True
    else:
        return False
