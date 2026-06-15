# rdt/reminder.py

import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime
import json
import os
from pathlib import Path
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

DATA_FILE = Path("data/reminders.json")

# ---------------- Persistent storage ----------------
def load_data():
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

reminders = load_data()

# ---------------- Helper ----------------
def is_staff(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        return True
    return any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles)

# ---------------- Setup function ----------------
def setup_reminder(bot: discord.Client, tree: app_commands.CommandTree):
    GUILD_ID = config.GUILD_ID

    # ---------------- Slash command with modal ----------------
    @app_commands.command(
        name="reminder",
        description="Create a staff-only reminder"
    )
    @app_commands.describe(
        channel="Channel to send the reminder in",
        role="Role to mention",
        role2="Additional role to mention",
        role3="Additional role to mention",
        role4="Additional role to mention",
        role5="Additional role to mention",
        role6="Additional role to mention",
        role7="Additional role to mention",
        role8="Additional role to mention",
        role9="Additional role to mention",
        role10="Additional role to mention"
    )
    async def reminder_command(
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role = None,
        role2: discord.Role = None,
        role3: discord.Role = None,
        role4: discord.Role = None,
        role5: discord.Role = None,
        role6: discord.Role = None,
        role7: discord.Role = None,
        role8: discord.Role = None,
        role9: discord.Role = None,
        role10: discord.Role = None
    ):
        if not is_staff(interaction):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.", ephemeral=True
            )
            return

        class ReminderModal(discord.ui.Modal, title="Create Reminder"):
            title_input = discord.ui.TextInput(label="Title", max_length=100)
            description_input = discord.ui.TextInput(
                label="Description", style=discord.TextStyle.paragraph
            )
            datetime_input = discord.ui.TextInput(
                label="Date & Time (YYYY-MM-DD HH:MM)",
                placeholder="2025-12-27 15:30"
            )
            images_input = discord.ui.TextInput(
                label="Image Links (Max 10)",
                placeholder="Link1, Link2, ... (Comma separated)",
                required=False
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    dt = datetime.strptime(self.datetime_input.value, "%Y-%m-%d %H:%M")
                except ValueError:
                    await modal_interaction.response.send_message(
                        "❌ Invalid date format. Use YYYY-MM-DD HH:MM", ephemeral=True
                    )
                    return

                selected_roles = [
                    r for r in [role, role2, role3, role4, role5, role6, role7, role8, role9, role10]
                    if r is not None
                ]

                images = []
                if self.images_input.value:
                    images = [url.strip() for url in self.images_input.value.split(',') if url.strip()][:10]

                reminder_data = {
                    "id": len(reminders) + 1,
                    "channel_id": channel.id,
                    "roles": [r.id for r in selected_roles],
                    "title": self.title_input.value,
                    "description": self.description_input.value,
                    "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
                    "images": images
                }

                reminders.append(reminder_data)
                save_data(reminders)

                await modal_interaction.response.send_message(
                    f"✅ Reminder created for {dt.strftime('%Y-%m-%d %H:%M')}",
                    ephemeral=True,
                )

        await interaction.response.send_modal(ReminderModal())

    # Register command
    if GUILD_ID:
        tree.add_command(reminder_command, guild=discord.Object(id=GUILD_ID))
    else:
        tree.add_command(reminder_command)

    print("Reminder command registered.")

    # ---------------- Reminder loop ----------------
    @tasks.loop(seconds=30)
    async def reminder_loop():
        now = datetime.now()
        to_remove = []

        for reminder in reminders:
            reminder_time = datetime.strptime(reminder["timestamp"], "%Y-%m-%d %H:%M")
            if now >= reminder_time:
                channel = bot.get_channel(reminder["channel_id"])
                if channel:
                    embed = discord.Embed(
                        title=reminder["title"],
                        description=reminder["description"],
                        color=config.EMBED_COLOR,
                    )

                    embeds = [embed]
                    images = reminder.get("images", [])
                    if images:
                        embed.set_image(url=images[0])
                        for img_url in images[1:]:
                            img_embed = discord.Embed(color=config.EMBED_COLOR)
                            img_embed.set_image(url=img_url)
                            embeds.append(img_embed)

                    mention_text = " ".join(f"<@&{r}>" for r in reminder["roles"])
                    await channel.send(content=mention_text or None, embeds=embeds)

                to_remove.append(reminder)

        for r in to_remove:
            reminders.remove(r)

        if to_remove:
            save_data(reminders)

    @reminder_loop.before_loop
    async def before_reminder_loop():
        await bot.wait_until_ready()

    return reminder_loop
