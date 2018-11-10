BOT_NAME=substitute-bot


clean:
	@echo "Quit previous session"
	screen -S ${BOT_NAME} -X quit

deploy: clean
	@echo "Start new session"
	screen -dmS ${BOT_NAME} python3 bot.py
