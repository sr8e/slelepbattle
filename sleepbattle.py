import re

from datetime import datetime, time, timedelta, timezone

import discord

from ui import who_to_attack
from db import DBManager
from settings import CHANNEL_ID, DISCORD_TOKEN, TIMEZONE


WAKEPATTERN = r"^(?:[お起]きた|起床|おはよう)(.+)?"
SLEEPPATTERN = r"^(?:[ね寝]る|就寝|おやすみ|ぽやしみ)(.+)?"
TIMESPECPATTERN = r"(\d{1,2}/\d{1,2})?\s*(\d{1,2}:\d{2})"

DISP_DATE_FORMAT = "%m/%d"
DISP_TIME_FORMAT = "%H:%M"
DISP_DATETIME_FORMAT = "%m/%d %H:%M"

intent = discord.Intents.default()
intent.members = True
client = discord.Client(intents=intent)


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
    habit_score = 1 if lastwaketime is None or abs(lastwaketime + timedelta(days=1) - waketime) < TD_HABIT else 0.9

    return date, 100 * sleep_score * wake_score * habit_score


def get_datetime_from_input(date, time):
    now = datetime.now().astimezone(tz=TIMEZONE)
    t = datetime.strptime(time, DISP_TIME_FORMAT).replace(tzinfo=TIMEZONE).timetz()
    if date is None:
        # interpret as the date is today or yesterday
        dt = datetime.combine(now.date(), t)
        if now < dt:
            dt -= timedelta(days=1)
        return dt

    d = datetime.strptime(date, DISP_DATE_FORMAT).date().replace(year=now.year)
    dt = datetime.combine(d, t)
    if now < dt:
        dt = dt.replace(year=dt.year - 1)
    return dt


def set_timezone(utctime):
    return utctime.replace(tzinfo=timezone.utc).astimezone(tz=TIMEZONE)


@client.event
async def on_ready():
    print(f'{client.user} is ready.')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel
    uid = message.author.id
    time = set_timezone(message.created_at)

    if isinstance(channel, discord.DMChannel):
        with DBManager() as db:
            state = db.get_attack_state(uid)
            if state == 0:
                d = time.date()
                week_start = d - timedelta(days=(d.weekday() + 1) % 7)
                uids = db.get_active_users(week_start)
                users = [client.get_user(u) for u in uids]
                if len(users) == 0:
                    await channel.send("攻撃可能な対象がまだいません。")
                    return

                await channel.send("対象を選択してください。", view=who_to_attack(users))
                db.set_attack_state(uid, 1)

    elif isinstance(channel, discord.TextChannel) and channel.id == CHANNEL_ID:

        if (match_s := re.search(SLEEPPATTERN, message.content, flags=re.M)) is not None:
            with DBManager() as db:
                if not db.is_last_sleep_completed(uid):
                    await channel.send("前回の睡眠が完了していません！")
                    return

                sleeptime = time
                if (spectime_s := match_s.group(1)) is not None:
                    if (match_spec_s := re.search(TIMESPECPATTERN, spectime_s)) is None:
                        await channel.send("時刻指定フォーマットに合致しません！(`[[m]m/[d]d] [H]H:MM`)")
                        return
                    sleeptime = get_datetime_from_input(*match_spec_s.group(1, 2))

                    last_wake = db.get_last_wake(uid)
                    if last_wake is not None and sleeptime < last_wake[1]:
                        await channel.send("就寝時刻が前回の起床より早いです。")
                        return

                db.insert_sleeptime(uid, sleeptime, message.id)
                await channel.send(f"睡眠を記録しました: {sleeptime.strftime(DISP_DATETIME_FORMAT)}")

        if (match_w := re.search(WAKEPATTERN, message.content, flags=re.M)) is not None:
            with DBManager() as db:
                if db.is_last_sleep_completed(uid):
                    await channel.send("睡眠が開始されていません！")
                    return

                waketime = time
                last_sleep = db.get_last_sleep(uid)
                if (spectime_w := match_w.group(1)) is not None:
                    if (match_spec_w := re.search(TIMESPECPATTERN, spectime_w)) is None:
                        await channel.send("時刻指定フォーマットに合致しません！(`[[m]m/[d]d] [H]H:MM`)")
                        return
                    waketime = get_datetime_from_input(*match_spec_w.group(1, 2))
                    if waketime < last_sleep[1]:
                        await channel.send("起床時刻が就寝より早いです。")
                        return

                last_wake = db.get_last_wake(uid)
                last_waketime = last_wake[1] if last_wake is not None else None

                wake_pk = db.insert_waketime(uid, waketime, message.id)
                await channel.send(f'起床を記録しました: {waketime.strftime(DISP_DATETIME_FORMAT)}')

                date, score = calculate_score(last_sleep[1], waketime, last_waketime)
                if (sameday_score := db.get_score(uid, date)) is None:
                    db.insert_score(uid, last_sleep[0], wake_pk, score, date)
                    await channel.send(f"{date.strftime(DISP_DATE_FORMAT)}のスコアを記録しました: {score:.4g}")
                elif sameday_score[3] < score:
                    db.update_score(sameday_score[0], last_sleep[0], wake_pk, score)
                    await channel.send(
                        f"{date.strftime(DISP_DATE_FORMAT)}のスコアを更新しました: "
                        f"{sameday_score[3]:.4g} -> {score:.4g}")
                else:
                    await channel.send(
                        f"{date.strftime(DISP_DATE_FORMAT)}の既存のスコア{sameday_score[3]:.4g}"
                        f"より低いので更新されませんでした: {score:.4g}"
                    )


client.run(DISCORD_TOKEN)
