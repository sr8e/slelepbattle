import os

from dotenv import load_dotenv


load_dotenv()
DISCORD_TOKEN = os.environ.get("DISCORDBOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))