from datetime import datetime

import discord

from db import DBManager
from settings import CHANNEL_ID, DISCORD_TOKEN, TIMEZONE


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

        today_scores = {t[1]: t[2] for t in db.get_day_score(date)}
        sorted_attacks = sorted(
            attacks,
            key=lambda t: today_scores[t[0]] if t[0] in today_scores else 0,
            reverse=True
        )

        for atk in sorted_attacks:
            my_uid, target_uid, swap_date = atk
            my_user = client.get_user(my_uid)
            target_user = client.get_user(target_uid)

            if today_scores[my_uid] > today_scores[target_uid]:
                r = {t[1]: t for t in db.get_compare_score(*atk, dur=False)}
                if (origin_score := r[my_uid][2]) < (target_score := r[target_uid][2]):
                    db.set_owner(r[my_uid][0], target_uid)
                    db.set_owner(r[target_uid][0], my_uid)
                    db.set_attack_state(my_uid, 5)
                    await channel.send(
                        f"{my_user.name} -> {target_user.name} の攻撃は成功しました。\n"
                        f"入れ替えられたスコア: {swap_date.strftime('%m/%d')}の {origin_score:.4g} <-> {target_score:.4g}"
                    )
                else:
                    db.delete_attack_record(my_uid)
                    await channel.send(
                        f"{my_user.name} -> {target_user.name} の攻撃は、入れ替え先のスコアのほうが低かったため、実行されませんでした。"
                        "(攻撃回数は消費されません)"
                    )
            else:
                db.set_attack_state(my_uid, 5)
                await channel.send(f"{my_user.name} -> {target_user.name} の攻撃は、失敗しました。")


@client.event
async def on_ready():
    print(f"{client.user} (for swap) is ready.")
    await swap()
    await client.close()

client.run(DISCORD_TOKEN)
