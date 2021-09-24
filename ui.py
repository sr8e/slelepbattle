import discord

from datetime import datetime, timedelta

from db import DBManager
from settings import DATE_FORMAT, TIMEZONE


class BaseSelect(discord.ui.Select):
    def __init__(self, view_manager, **kwargs):
        self.vm = view_manager
        self.uid = self.vm.uid
        self.init_date = self.vm.init_date
        super().__init__(**kwargs)

    def week_start(self):
        return self.init_date - timedelta(days=(self.init_date.weekday() + 1) % 7)


class SelectTarget(BaseSelect):
    async def callback(self, interaction):
        target = int(interaction.data['values'][0])

        with DBManager() as db:
            if db.get_attack_state(self.uid) != 1:
                return

            score_tup = db.get_compare_score(self.uid, target, self.week_start())

        scores = {}
        for t in score_tup:
            if t[3] not in scores:
                scores[t[3]] = {}
            scores[t[3]][t[1]] = t[2]
        swappable = {d: v for d, v in scores.items() if len(v) == 2 and v[self.uid] < v[target]}

        if len(swappable) == 0:
            await interaction.response.edit_message(
                content="入れ替え可能な日がありません。別の対象を選択してください。",
                view=self.vm.who_to_attack()
            )

        view = self.vm.when_to_swap(swappable, target)

        await interaction.response.edit_message(content="スコアを入れ替える日を選択してください。", view=view)
        with DBManager() as db:
            db.set_target(self.uid, target)


class SelectSwapDate(BaseSelect):
    async def callback(self, interaction):
        swap_date = datetime.strptime(interaction.data['values'][0], DATE_FORMAT).date()

        week_start = self.week_start()
        attackable = [
            week_start + timedelta(days=i)
            for i in range((self.init_date.weekday() + 1) % 7 + 2, 9)
        ]

        with DBManager() as db:
            if db.get_attack_state(self.uid) != 2:
                return

            db.set_swap_date(self.uid, swap_date)

        view = self.vm.when_to_attack(attackable)
        await interaction.response.edit_message(content="攻撃を実行する日を選択してください。", view=view)


class SelectAttackDate(BaseSelect):
    async def callback(self, interaction):
        attack_date = datetime.strptime(interaction.data['values'][0], DATE_FORMAT).date()

        with DBManager() as db:
            if db.get_attack_state(self.uid) != 3:
                return

            db.set_attack_date(self.uid, attack_date, datetime.now().astimezone(tz=TIMEZONE))
            info = db.get_attack_info(self.uid)

        target_u = self.vm.client.get_user(info[1])

        await interaction.response.edit_message(
            content=f"攻撃の予約を完了しました (対象: {target_u.name}, 入替日: {info[2].strftime('%m/%d')}, "
                    f"攻撃日: {attack_date.strftime('%m/%d')})",
            view=None
        )


class UIViewManager:
    def __init__(self, uid, client, init_date):
        self.client = client
        self.init_date = init_date
        self.uid = uid

    async def begin_configure(self, channel):
        with DBManager() as db:
            state = db.get_attack_state(self.uid)

            if state != 0:
                return

            week_start = self.init_date - timedelta(days=(self.init_date.weekday() + 1) % 7)
            uids = db.get_active_users(week_start)

            self.users = [self.client.get_user(u) for u in uids if u != self.uid]
            if len(self.users) == 0:
                await channel.send("攻撃可能な対象がまだいません。")
                return

            await channel.send("対象を選択してください。", view=self.who_to_attack())
            db.set_attack_state(self.uid, 1)

    def who_to_attack(self):
        view = discord.ui.View(timeout=60)
        options = [discord.SelectOption(label=u.name, value=u.id) for u in self.users]
        selection = SelectTarget(
            self,
            placeholder="攻撃対象を選択...",
            options=options
        )
        view.add_item(selection)
        return view

    def when_to_swap(self, swappable_dates, target):
        view = discord.ui.View(timeout=60)
        options = [
            discord.SelectOption(
                label=d.strftime("%m/%d (%a)"),
                value=d.strftime(DATE_FORMAT),
                description=f"Your Point: {v[self.uid]:.4g}, Target's Point: {v[target]:.4g}"
            )
            for d, v in swappable_dates.items()
        ]
        selection = SelectSwapDate(
            self,
            placeholder="スコアを入れ替える日を選択...",
            options=options
        )
        view.add_item(selection)
        return view

    def when_to_attack(self, attackable_dates):
        view = discord.ui.View(timeout=60)
        options = [
            discord.SelectOption(
                label=d.strftime("%m/%d (%a)"),
                value=d.strftime(DATE_FORMAT)
            )
            for d in attackable_dates
        ]
        selection = SelectAttackDate(
            self,
            placeholder="攻撃をする日を選択...",
            options=options
        )
        view.add_item(selection)
        return view
