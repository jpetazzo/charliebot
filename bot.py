#!/usr/bin/env python

import functools
import logging
import openai
import os
import telegram
import telegram.ext

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

openai.api_key = os.environ["OPENAI_API_KEY"]
BOT_NAME = os.environ["BOT_NAME"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PERSISTENCE_FILE = os.environ["PERSISTENCE_FILE"]
DEBUG = os.environ.get("DEBUG", "no").lower() in ["yes", "y", "on", "1", "true"]

prompt = f"""You are {BOT_NAME}, an experienced business coach with more than 20 years of experience.
You will be assisting and advising your client with all their questions.
You have a positive, optimistic attitude.

If you don't know the name and pronouns of your client, you will start by asking that.
Otherwise, you will greet them by name.
You will start the conversation with a little bit of smalltalk.
Then you will enquire about their current concerns on their project, and advise them as best as possible.
When many options are available, you will help them to narrow them down by asking additional questions.

When you receive a message consisting of a sole "💾" you will respond with a message listing the facts that you have learned so far about your client, one per line, in bullet point format, where the first bullet point should indicate their name and preferred pronouns, and the following bullet points should include facts gathered during previous conversations."""

first_message = f"""Hi {BOT_NAME}!"""

async def streaming_reply(update, context):
  log.info(f"Processing message for user {update.effective_user.full_name}.")
  await context.bot.send_chat_action(
    chat_id=update.effective_chat.id,
    action=telegram.constants.ChatAction.TYPING
  )
  messages = context.chat_data["messages"]
  if "facts" in context.chat_data:
    facts = "\n\n" + context.chat_data["facts"]
  else:
    facts = ""
  system_message = dict(role="system", content=prompt+facts)
  response_stream = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[system_message] + messages,
    stream=True,
  )
  full_response = ""
  last_paragraph = ""
  is_gathering_facts = messages[-1]["content"][0] == "💾"
  for chunk in response_stream:
    chunk_delta = chunk["choices"][0]["delta"]
    if "role" in chunk_delta:
      role = chunk_delta.pop("role")
      assert role == "assistant"
    if "content" in chunk_delta:
      chunk_text = chunk_delta.pop("content")
      DEBUG and print(chunk_text, end="", flush=True)
      full_response += chunk_text
      last_paragraph += chunk_text
      if last_paragraph.endswith("\n\n") and last_paragraph.strip() and not is_gathering_facts:
        await context.bot.send_message(
          chat_id=update.effective_chat.id,
          text=last_paragraph.strip("\n"),
        )
        last_paragraph = ""
        await context.bot.send_chat_action(
          chat_id=update.effective_chat.id,
          action=telegram.constants.ChatAction.TYPING
        )
    if chunk_delta:
      log.warn("Extra data in chunk delta:", chunk_delta)
    finish_reason = chunk["choices"][0]["finish_reason"]
    if finish_reason != None:
      break
  DEBUG and print()
  assert finish_reason == "stop", repr(chunk)
  if is_gathering_facts:
    context.chat_data["facts"] = full_response
    del messages[-1]
  else:
    await context.bot.send_message(
      chat_id=update.effective_chat.id,
      text=last_paragraph.strip("\n"),
    )
    messages.append(dict(role="assistant", content=full_response))

persistence = telegram.ext.PicklePersistence(filepath=PERSISTENCE_FILE)
telegram_application = (
  telegram.ext.ApplicationBuilder()
  .token(TELEGRAM_BOT_TOKEN)
  .persistence(persistence=persistence)
  .build()
)

bot_commands = []
async def post_init(app):
  await app.bot.set_my_commands(bot_commands)
telegram_application.post_init = post_init

def bot_command(command_name, command_description):
  bot_commands.append((command_name, command_description))
  def decorator(func):
    @functools.wraps(func)
    async def newfunc(update, context):
      log.info(f"Processing command '{command_name}' for user {update.effective_user.full_name}.")
      return await func(update, context)
    telegram_application.add_handler(
      telegram.ext.CommandHandler(command_name, newfunc)
    )
  return decorator

@bot_command("start", f"start a new appointment with {BOT_NAME}")
async def start(update, context):
  context.chat_data["messages"] = [
    dict(role="user", content=first_message)
  ]
  await streaming_reply(update, context)

@bot_command("dossier", f"ask {BOT_NAME} for the content of your dossier")
async def dossier(update, context):
  context.chat_data["messages"].append(
    dict(role="user", content="💾")
  )
  await streaming_reply(update, context)
  dossier = context.chat_data.get("facts")
  await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text=dossier
  )

@bot_command("clear", f"{BOT_NAME} will forget everything about you")
async def clear(update, context):
  context.chat_data.clear()
  await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="🧹♻️"
  )
  await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="OK, I've forgotten everything about you!"
  )

async def echo(update, context):
  context.chat_data["messages"].append(
    dict(role="user", content=update.message.text)
  )
  await streaming_reply(update, context)

telegram_application.add_handler(
  telegram.ext.MessageHandler(
    telegram.ext.filters.TEXT & (~telegram.ext.filters.COMMAND),
    echo
  )
)

telegram_application.run_polling()

