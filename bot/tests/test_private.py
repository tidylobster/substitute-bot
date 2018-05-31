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
    generated_name = "kenholm7"

    response = client.send_command_await("/create", num_expected=1)
    response = client.send_message_await(generated_name, num_expected=1)
    assert response.full_text.startswith('Saved'), "Correctly saved responses start with 'Saved.'"

    response = client.send_command_await("/groups", num_expected=1)
    for row in response.inline_keyboards[0].rows:
        assert len(row) == 1, "Each row should be of length 1"
        if row[0].text.startswith(generated_name): break
    else:
        assert False, "Cannot find created group in the list"