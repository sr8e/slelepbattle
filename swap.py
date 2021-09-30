import sys
from datetime import datetime

import discord

from db import DBManager
from settings import CHANNEL_ID, DISCORD_TOKEN, TIMEZONE

action = sys.argv[1]
intent = discord.Intents.default()
intent.members = True
client = discord.Client(intents=intent)

date = datetime.now().astimezone(tz=TIMEZONE).date()


async def swap():
    channel = client.get_channel(CHANNEL_ID)
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


async def reset_stock():
    channel = client.get_channel(CHANNEL_ID)
    with DBManager() as db:
        db.reset_attack_record()
        await channel.send("攻撃のストックがリセットされました。")


@client.event
async def on_ready():
    print(f"{client.user} (for swap) is ready.")
    if action == "swap":
        await swap()
    elif action == "reset":
        await reset_stock()
    await client.close()


client.run(DISCORD_TOKEN)
