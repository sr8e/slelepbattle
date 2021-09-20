import discord

from datetime import datetime, timedelta

from db import DBManager
from settings import DATE_FORMAT


class SelectTarget(discord.ui.Select):
    async def callback(self, interaction):
        target = int(interaction.data['values'][0])
        uid_s, date_s, _ = interaction.data['custom_id'].split('_')
        uid = int(uid_s)
        date = datetime.strptime(date_s, DATE_FORMAT).date()
        week_start = date - timedelta(days=(date.weekday() + 1) % 7)

        with DBManager() as db:
            if db.get_attack_state(uid) != 0:
                return

            score_tup = db.get_compare_score(uid, target, week_start)

        scores = {}
        for t in score_tup:
            if t[3] not in scores:
                scores[t[3]] = {}
            scores[t[3]][t[1]] = t[2]
        scores = {d: scores[d] for d in scores if len(scores[d]) == 2 and scores[d][uid] < scores[d][target]}
        if len(scores) == 0:
            await interaction.response.send_message("入れ替え可能な日がありません。別の対象を選択してください。")

        await interaction.response.send_message("スコアを入れ替える日を選択してください。")


def who_to_attack(uid, users, date):
    view = discord.ui.View(timeout=60)
    options = [discord.SelectOption(label=u.name, value=u.id) for u in users]
    selection = SelectTarget(
        custom_id=f"{uid}_{date.strftime(DATE_FORMAT)}_TARGET",
        placeholder="攻撃対象を選択...",
        options=options
    )
    view.add_item(selection)
    return view
