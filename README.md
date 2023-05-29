# Charlie Ze Bot

> Two API clients in a Python trenchcoat.

Charlie Ze Bot is a Telegram bot that uses OpenAI ChatGPT model
to provide chat-like interaction.

To run it, install its dependencies:

```bash
pip install -r requirements.txt
```

Obtain an OpenAI API key (https://platform.openai.com/account/api-keys) and
a Telegram Bot Token (by interacting with @BotFather on Telegram) then set
the following environment variables:

```bash
export OPENAI_API_KEY=sk-XXX...
export BOT_NAME=Whatever
export TELEGRAM_BOT_TOKEN=12345678:ABCDE...
export PERSISTENCE_FILE=whatever.pck
```

Then run `bot.py`.

It's persisting its state in the `.pck` file, which means that you can stop
and restart it at any time.

## What else

This is very low quality code and should probably be entirely rewritten,
but it was a very fun experiment :)

Feel free to do whatever you want with it!
