import pytest
from tgintegration import BotIntegrationClient
from decouple import Config, RepositoryEnv


@pytest.fixture(scope="session")
def client():
    config = Config(RepositoryEnv('config.env'))
    c = BotIntegrationClient(
        bot_under_test=config('BOT_NAME'),
        session_name='my_account',
        api_id=config('API_ID'),
        api_hash=config('API_HASH'),
        proxy=dict(
            hostname="195.201.136.50",
            port=30080,
            username="telegram",
            password="barsv808au"
        ),
        max_wait_response=15,
        min_wait_consecutive=2,
        global_action_delay=1)

    c.start()
    yield c  # py.test sugar to separate setup from teardown
    c.stop()


def test_start(client: BotIntegrationClient):
    response = client.send_command_await("/start", num_expected=1)

    assert response.num_messages == 1
    assert response.full_text.startswith("Hello")


def test_create_group_abort(client: BotIntegrationClient):
    response = client.send_command_await("/create", num_expected=1)
    assert response.num_messages == 1
    assert response.full_text.startswith("Ok, send the name of the group")

    response = client.send_command_await("/cancel", num_expected=1)
    assert response.num_messages == 1
    assert response.full_text.startswith("Sure, what now?")


def test_create_group_with_valid_symbols(client: BotIntegrationClient):
    generated_name = "kenholss"

    client.send_command_await("/create", num_expected=1)
    response = client.send_message_await(generated_name, num_expected=1)

    assert response.full_text.startswith('Saved'), "Correctly saved responses start with 'Saved.'"
    assert group_is_existing(client, generated_name), "Cannot find created group in the list"


# def test_commands(client: BotIntegrationClient):
#     # The BotIntegrationClient automatically loads the available commands and we test them all here
#     for c in client.command_list:
#         res = client.send_command_await(c.command)
#         assert not res.empty, "Bot did not respond to command /{}.".format(c.command)


def test_rename_existing_group(client: BotIntegrationClient):
    name = "tesrenameexistingroup"
    if not group_is_existing(client, name):
        create_group_command(client, name)

    rename_group_command(client, name)

def test_delete_existing_group(client: BotIntegrationClient):
    name = "testexistinggroup"
    if not group_is_existing(client, name):
        create_group_command(client, name)

    delete_group_command(client, name)

def test_add_members_from_existing_group(client: BotIntegrationClient):
    print()


def test_remove_members_from_existing_group(client: BotIntegrationClient):
    print()

def test_integration_create_rename_delete_group(client: BotIntegrationClient):
    name = "testrename"

    create_group_command(client, name)
    rename_group_command(client, name)
    delete_group_command(client, name+"renamed")


### Support functions

def create_group_command(client: BotIntegrationClient, generated_name: str):
    bot_send_tg_command(client, "/create")
    response = bot_send_tg_message(client, generated_name)

    assert response.full_text.startswith('Saved'), "Correctly saved responses start with 'Saved.'"

def rename_group_command(client: BotIntegrationClient, name: str):
    response = bot_call_gropup_command(client)

    pattern = r'.*{} | 1 member(s)'.format(name)

    group_name = response.inline_keyboards[0].press_button_await(pattern=pattern)

    assert not group_name.empty, 'Pressing "group_name" button had no effect.'
    assert name.lower() in group_name.full_text.lower()

    renamed = name + "renamed"
    group_name.inline_keyboards[0].press_button_await(pattern=r'.*Rename group', min_wait_consecutive=3)
    bot_send_tg_message(client, renamed)

    assert group_is_existing(client, renamed)

def delete_group_command(client: BotIntegrationClient, name: str):
    assert group_is_existing(client, name)

    response = bot_call_gropup_command(client)
    pattern = r'.*{} | 1 member(s)'.format(name)
    response = response.inline_keyboards[0].press_button_await(pattern=pattern, min_wait_consecutive=3)
    delete_group = response.inline_keyboards[0].press_button_await(pattern=r'.*Delete group', min_wait_consecutive=3)
    delete_group.inline_keyboards[0].press_button_await(pattern=r'.*Yes', min_wait_consecutive=3)

    assert not (group_is_existing(client, name))

def group_is_existing(client: BotIntegrationClient, group_name: str):
    response = client.send_command_await("/groups", num_expected=1)
    for row in response.inline_keyboards[0].rows:
        assert len(row) == 1, "Each row should be of length 1"
        if row[0].text.startswith(group_name):
            return True
    else:
        return False

def bot_send_tg_command(client: BotIntegrationClient, command:str):
    return client.send_command_await(command, num_expected=1)

def bot_send_tg_message(client: BotIntegrationClient, message: str):
    return client.send_message_await(message)

def bot_call_gropup_command(client: BotIntegrationClient):
    return bot_send_tg_command(client, "/groups")

def bot_call_create_command(client: BotIntegrationClient):
    return bot_send_tg_command(client, "/create")