import re
import os

from datetime import date, datetime, time, timedelta, timezone

import discord

from db import insert_sleeptime
from settings import CHANNEL_ID, DISCORD_TOKEN, TIMEZONE


WAKEPATTERN = r"^(?:[お起]きた|起床|おはよう)(.+)?"
SLEEPPATTERN = r"^(?:[ね寝]る|就寝|おやすみ|ぽやしみ)(.+)?"
TIMESPECPATTERN = r"(\d{1,2}/\d{1,2})?\s*(\d{1,2}:\d{2})"

client = discord.Client()


def calculate_score(sleeptime, waketime, lastwaketime):
    date = (waketime + timedelta(hours=5, minutes=30)).date()
    sleep_f = datetime.combine(date - timedelta(days=1), time(hour=22, tzinfo=TIMEZONE))
    sleep_l = datetime.combine(date, time(hour=1, tzinfo=TIMEZONE))
    wake_f = datetime.combine(date, time(hour=5, tzinfo=TIMEZONE))
    wake_l = datetime.combine(date, time(hour=8, tzinfo=TIMEZONE))

    TD_ZERO = timedelta()
    TD_HABIT = timedelta(hours=3)
    TD_WIDTH = timedelta(hours=10)

    sleep_score = max(1 - max(sleep_f - sleeptime, sleeptime - sleep_l, TD_ZERO) / TD_WIDTH, 0)
    wake_score = max(1 - max(wake_f - waketime, waketime - wake_l, TD_ZERO) / TD_WIDTH, 0)
    habit_score = 1 if abs(lastwaketime + timedelta(days=1) - waketime) < TD_HABIT else 0.9
    print(f"{sleep_score}, {wake_score}, {habit_score}")

    return date, 100 * sleep_score * wake_score * habit_score


def get_datetime_from_input(date, time):
    now = datetime.now().astimezone(tz=TIMEZONE)
    t = datetime.strptime(time, "%H:%M").replace(tzinfo=TIMEZONE).timetz()
    if date is None:
        # interpret as the date is today or yesterday
        dt = datetime.combine(now.date(), t)
        if now < dt:
            dt -= timedelta(days=1)
        return dt

    d = datetime.strptime(date, "%m/%d").date().replace(year=now.year)
    dt = datetime.combine(d, t)
    if now < dt:
        dt = dt.replace(year=dt.year - 1)
    return dt


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
        time = message.created_at.replace(tzinfo=timezone.utc).astimezone(tz=TIMEZONE)

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
                insert_sleeptime(message.author.id, time)

client.run(DISCORD_TOKEN)
