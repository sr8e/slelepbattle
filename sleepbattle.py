import re
from datetime import datetime, time, timedelta, timezone

import discord

from db import DBManager
from settings import CHANNEL_ID, DISCORD_TOKEN, TIMEZONE
from ui import UIViewManager

WAKEPATTERN = r"^(?:[お起]きた|起床|おはよう)(.+)?"
SLEEPPATTERN = r"^(?:[ね寝]る|就寝|おやすみ|ぽやしみ)(.+)?"
TIMESPECPATTERN = r"(\d{1,2}/\d{1,2})?\s*(\d{1,2}:\d{2})"

DISP_DATE_FORMAT = "%m/%d"
DISP_TIME_FORMAT = "%H:%M"
DISP_DATETIME_FORMAT = "%m/%d %H:%M"

intent = discord.Intents.default()
intent.members = True
intent.message_content = True
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
    habit_score = (
        1
        if lastwaketime is None or abs(lastwaketime + timedelta(days=1) - waketime) < TD_HABIT
        else 0.9
    )

    return date, sleep_score, wake_score, habit_score


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
    print(f"{client.user} is ready.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel = message.channel
    uid = message.author.id
    post_time = set_timezone(message.created_at)

    if isinstance(channel, discord.DMChannel):
        with DBManager() as db:
            state = db.get_attack_state(uid)

            if message.content.startswith("abort"):
                if 0 < state < 4:
                    db.delete_attack_record(uid)
                    await channel.send("攻撃の設定を中断しました。")
                else:
                    await channel.send("そのコマンドは今は使えません。")
                return

            if message.content.startswith("cancel"):
                if state != 4:
                    await channel.send("そのコマンドは今は使えません。")
                    return

                atk = db.get_attack_info(uid)
                limit = datetime.combine(
                    atk.attack_date, time(hour=18, minute=30, tzinfo=TIMEZONE)
                ) - timedelta(days=1)
                if post_time < limit:
                    db.delete_attack_record(uid)
                    await channel.send("攻撃を中止しました。")
                else:
                    await channel.send("攻撃中止の期限を過ぎています。")
                return

        if 0 < state < 4:
            await channel.send("攻撃の設定が途中です。`abort` で中断します。")
            return
        if state == 4:
            await channel.send("攻撃の設定が完了しています。`cancel` で攻撃を中止できます。")
            return
        if state == 5:
            await channel.send("攻撃は完了しています。")
            return

        vm = UIViewManager(uid, client, post_time.date())
        await vm.begin_configure(channel)

    elif isinstance(channel, discord.TextChannel) and channel.id == CHANNEL_ID:

        if (match_s := re.search(SLEEPPATTERN, message.content, flags=re.M)) is not None:
            with DBManager() as db:
                if not db.is_last_sleep_completed(uid):
                    await channel.send("前回の睡眠が完了していません！")
                    return

                sleeptime = post_time
                if (spectime_s := match_s.group(1)) is not None:
                    if (match_spec_s := re.search(TIMESPECPATTERN, spectime_s)) is None:
                        await channel.send("時刻指定フォーマットに合致しません！(`[[m]m/[d]d] [H]H:MM`)")
                        return
                    sleeptime = get_datetime_from_input(*match_spec_s.group(1, 2))

                    last_wake = db.get_last_wake(uid)
                    if last_wake is not None and sleeptime < last_wake.waketime:
                        await channel.send("就寝時刻が前回の起床より早いです。")
                        return

                db.insert_sleeptime(uid, sleeptime, message.id)
                await channel.send(f"睡眠を記録しました: {sleeptime.strftime(DISP_DATETIME_FORMAT)}")

        if (match_w := re.search(WAKEPATTERN, message.content, flags=re.M)) is not None:
            with DBManager() as db:
                if db.is_last_sleep_completed(uid):
                    await channel.send("睡眠が開始されていません！")
                    return

                waketime = post_time
                last_sleep = db.get_last_sleep(uid)
                if (spectime_w := match_w.group(1)) is not None:
                    if (match_spec_w := re.search(TIMESPECPATTERN, spectime_w)) is None:
                        await channel.send("時刻指定フォーマットに合致しません！(`[[m]m/[d]d] [H]H:MM`)")
                        return
                    waketime = get_datetime_from_input(*match_spec_w.group(1, 2))
                    if waketime < last_sleep.sleeptime:
                        await channel.send("起床時刻が就寝より早いです。")
                        return

                last_wake = db.get_last_wake(uid)
                last_waketime = last_wake.waketime if last_wake is not None else None

                wake_pk = db.insert_waketime(uid, waketime, message.id)
                await channel.send(f"起床を記録しました: {waketime.strftime(DISP_DATETIME_FORMAT)}")

                date, ss, ws, hs = calculate_score(last_sleep.sleeptime, waketime, last_waketime)
                score = 100 * ss * ws * hs
                if (sameday_score := db.get_raw_score(uid, date)) is None:
                    db.insert_score(uid, last_sleep.pk, wake_pk, score, date)
                    await channel.send(
                        f"{date.strftime(DISP_DATE_FORMAT)}のスコアを記録しました: "
                        f"100 x {ss:.2f} x {ws:.2f} x {hs:.2f} = {score:.4g}"
                    )
                elif sameday_score.score < score:
                    db.update_score(sameday_score.pk, last_sleep.pk, wake_pk, score)
                    await channel.send(
                        f"{date.strftime(DISP_DATE_FORMAT)}のスコアを更新しました: "
                        f"100 x {ss:.2f} x {ws:.2f} x {hs:.2f} = {score:.4g}\n"
                        f"(更新前のスコア: {sameday_score.score:.4g})"
                    )
                else:
                    await channel.send(
                        f"{date.strftime(DISP_DATE_FORMAT)}の既存のスコア{sameday_score.score:.4g}"
                        f"より低いので更新されませんでした: 100 x {ss:.2f} x {ws:.2f} x {hs:.2f} = {score:.4g}"
                    )


client.run(DISCORD_TOKEN)
