import re
import os

import discord

from settings import CHANNEL_ID, DISCORD_TOKEN


WAKEPATTERN = r"^(?:[お起]きた|起床|おはよう)(.+)?"
SLEEPPATTERN = r"^(?:[ね寝]る|就寝|おやすみ|ぽやしみ)(.+)?"

client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} is ready.')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel

    if isinstance(channel, discord.DMChannel):
        pass
        # todo: surprise attack
    elif isinstance(channel, discord.TextChannel) and channel.id == CHANNEL_ID:
        if (match_w := re.match(WAKEPATTERN, message.content)) is not None:
            if (overwrite_w := match_w.group(1)) is not None:
                pass
                # todo: overwrite
            else:
                pass
                # todo: calculate and store the score

        elif (match_s := re.match(SLEEPPATTERN, message.content)) is not None:
            if (overwrite_s := match_s.group(1)) is not None:
                pass
                # todo: overwrite
            else:
                pass
                # todo: memory the time

client.run(DISCORD_TOKEN)
