import discord
from discord import app_commands
from discord.ext import commands
import os, json
from dotenv import load_dotenv

import config

load_dotenv()
STAFF_ROLE_ID = config.STAFF_ROLE_ID
STATUS_FILE = "data/status.json"

STATUS_TYPES = {
    "Watching": discord.ActivityType.watching,
    "Playing": discord.ActivityType.playing,
    "Listening": discord.ActivityType.listening,
    "Competing": discord.ActivityType.competing
}

def save_status(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_status():
    if not os.path.exists(STATUS_FILE):
        return None
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

class StatusTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=x) for x in STATUS_TYPES]
        super().__init__(placeholder="Select status type...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_type = self.values[0]
        await interaction.response.defer()

class StatusView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.selected_type = "Watching"
        self.add_item(StatusTypeSelect())

class StatusModal(discord.ui.Modal, title="Bot Status"):
    status_text = discord.ui.TextInput(
        label="Status Text",
        placeholder="VTC Members",
        max_length=128
    )

    emoji = discord.ui.TextInput(
        label="Emoji (optional)",
        placeholder="👀 or <:custom:123456789>",
        required=False,
        max_length=50
    )

    def __init__(self, status_type):
        super().__init__()
        self.status_type = status_type

    async def on_submit(self, interaction: discord.Interaction):
        if not any(r.id in STAFF_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True)
            return

        name = f"{self.emoji.value} {self.status_text.value}".strip()

        await interaction.client.change_presence(
            activity=discord.Activity(
                type=STATUS_TYPES[self.status_type],
                name=name
            ),
            status=discord.Status.online
        )

        save_status({
            "type": self.status_type,
            "text": self.status_text.value,
            "emoji": self.emoji.value
        })

        await interaction.response.send_message(
            f"✅ Saved & set status: **{self.status_type} {name}**",
            ephemeral=True
        )

def setup_bot_present(bot: commands.Bot):
    @bot.tree.command(
        name="bot_present",
        description="Change bot status (staff only)"
    )
    async def bot_present(interaction: discord.Interaction):
        if not any(r.id in STAFF_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True)
            return

        view = StatusView()

        async def next_callback(inter: discord.Interaction):
            await inter.response.send_modal(StatusModal(view.selected_type))

        button = discord.ui.Button(label="Next", style=discord.ButtonStyle.green)
        button.callback = next_callback
        view.add_item(button)

        await interaction.response.send_message(
            "Select status type then press **Next**",
            view=view,
            ephemeral=True
        )

async def restore_status(bot: commands.Bot):
    data = load_status()
    if not data:
        return

    name = f"{data.get('emoji', '')} {data.get('text', '')}".strip()
    await bot.change_presence(
        activity=discord.Activity(
            type=STATUS_TYPES.get(data["type"], discord.ActivityType.watching),
            name=name
        ),
        status=discord.Status.online
    )
    