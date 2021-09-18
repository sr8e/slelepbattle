import discord


def who_to_attack(uid, users):
    view = discord.ui.View(timeout=60)
    options = [discord.SelectOption(label=u.name, value=u.id) for u in users if u.id != uid]
    selection = discord.ui.Select(placeholder="攻撃対象を選択...", options=options)
    view.add_item(selection)
    return view
