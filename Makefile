BOT_NAME=substitute-bot
BOT_TEST_NAME=substitute-bot-testing


test_bot_instance: 
	@echo "Creating new testing session"
	screen -dmS ${BOT_TEST_NAME} python3 bot.py

test_run: test_bot_instance
	@echo "Running tests"
	pytest

test: test_run
	@echo "Tearing down testing session"
	screen -S ${BOT_TEST_NAME} -X quit

clean:
	@echo "Quit previous session"
	screen -S ${BOT_NAME} -X quit

deploy: clean
	@echo "Start new session"
	screen -dmS ${BOT_NAME} python3 bot.py
