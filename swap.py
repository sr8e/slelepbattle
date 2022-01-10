import sys
from datetime import datetime, timedelta

import discord

from db import DBManager
from settings import DISCORD_TOKEN, NOTIFY_CHANNEL_ID, TIMEZONE

action = sys.argv[1]
intent = discord.Intents.default()
intent.members = True
client = discord.Client(intents=intent)

date = datetime.now().astimezone(tz=TIMEZONE).date()


async def swap():
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    with DBManager() as db:
        attacks = db.get_standby_attack(date)
        if len(attacks) == 0:
            await channel.send(f"{date.strftime('%m/%d')}の攻撃はありませんでした。")
            return

        today_scores = {s.uid: s.score for s in db.get_day_score(date)}
        sorted_attacks = sorted(attacks, key=lambda atk: today_scores.get(atk.uid, 0), reverse=True)

        for atk in sorted_attacks:
            my_uid = atk.uid
            target_uid = atk.target
            my_user = client.get_user(my_uid)
            target_user = client.get_user(target_uid)

            if today_scores.get(my_uid, 0) > today_scores.get(target_uid, 0):
                r = {
                    s.owner: s
                    for s in db.get_compare_score(my_uid, target_uid, atk.swap_date, dur=False)
                }
                if (origin_record := r[my_uid]).score < (target_record := r[target_uid]).score:
                    db.set_owner(origin_record.pk, target_uid)
                    db.set_owner(target_record.pk, my_uid)
                    db.set_attack_state(my_uid, 5)
                    await channel.send(
                        f"{my_user.name} -> {target_user.name} の攻撃は成功しました。\n"
                        f"入れ替えられたスコア: {atk.swap_date.strftime('%m/%d')}の"
                        f"{origin_record.score:.4g} <-> {target_record.score:.4g}"
                    )
                else:
                    db.delete_attack_record(my_uid)
                    await channel.send(
                        f"{my_user.name} -> {target_user.name} の攻撃は、入れ替え先のスコアのほうが低かったため、"
                        "実行されませんでした。(攻撃回数は消費されません)"
                    )
            else:
                db.set_attack_state(my_uid, 5)
                await channel.send(f"{my_user.name} -> {target_user.name} の攻撃は、失敗しました。")


async def export_table(prev=False):
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    d = datetime.now().astimezone(TIMEZONE).date()
    if not prev and (d.weekday() + 1) % 7 < 2:
        await export_table(True)

    week_start = d - timedelta(days=(d.weekday() + 1) % 7)
    if prev:
        week_start -= timedelta(days=7)

    with DBManager() as db:
        scores = db.get_week_score(week_start)

    scores_dict = {}
    for s in scores:
        if s.uid not in scores_dict:
            scores_dict[s.owner] = {}
        scores_dict[s.owner][s.date] = s

    days = 7 if prev else (d.weekday() + 1) % 7 + 1
    for owner, v in scores_dict.items():
        scores_dict[owner]["avg"] = sum(map(lambda s: s.score, v.values())) / days

    owners_sorted = sorted(scores_dict, key=lambda k: scores_dict[k]["avg"], reverse=True)

    week_val = "先" if prev else "今"
    table = f"{week_val}週の順位表({d.strftime('%m/%d')}現在)```Pos | "
    for i in range(7):
        table += (week_start + timedelta(days=i)).strftime(" %m/%d ")
    table += (
        "|  Avg   | Name\n"
        "====+==================================================+========+===============\n"
    )
    for i, owner in enumerate(owners_sorted):
        user_scores = scores_dict[owner]
        table += f"{i + 1:>2}. | "
        for j in range(7):
            key_date = week_start + timedelta(days=j)
            if key_date not in user_scores:
                table += "------ "
            else:
                s = user_scores[key_date]
                score_str = f"{s.score:>6.2f}"
                table += f"{score_str} " if s.owner == s.uid else f"{score_str}*"

        table += f"| {user_scores['avg']:>6.2f} | {client.get_user(owner).name}\n"
    table += "```"

    await channel.send(table)


async def reset_stock():
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    with DBManager() as db:
        db.reset_attack_record()
        await channel.send("攻撃のストックがリセットされました。")


@client.event
async def on_ready():
    print(f"{client.user} (for swap) is ready.")
    if action == "swap":
        await swap()
        await export_table()
    elif action == "reset":
        await reset_stock()
    await client.close()


client.run(DISCORD_TOKEN)
