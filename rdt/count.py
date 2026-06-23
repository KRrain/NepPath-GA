import discord
from discord.ext import commands
import os
import sys
import json
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

DATA_FILE = Path("data/count_data.json")

# Only this channel ID will have counting enabled
COUNT_CHANNEL_ID = 1518799156242681877

# ---------------- Persistent storage ----------------
def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

count_data = load_data()

def is_staff(member: discord.Member):
    return member.guild_permissions.administrator or any(role.id in config.STAFF_ROLE_ID for role in member.roles)

def setup_count(bot: commands.Bot):
    @bot.tree.command(name="resetcount", description="Reset the count back to 0 (Staff only)")
    async def resetcount(interaction: discord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)

        if guild_id not in count_data:
            count_data[guild_id] = {"channels": {}}

        channels = count_data[guild_id]["channels"]
        channels[channel_id] = {
            "last_count": 0,
            "last_user_id": None
        }
        save_data(count_data)

        embed = discord.Embed(
            title="🔄 Count Reset",
            description=f"Count has been reset to **0** in {interaction.channel.mention}",
            color=config.EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)

    # Register the command to the guild
    if hasattr(config, "GUILD_ID") and config.GUILD_ID:
        bot.tree.add_command(resetcount, guild=discord.Object(id=config.GUILD_ID))

    @bot.event
    async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
        """Remove user reactions in the counting channel - only bot reactions allowed"""
        if reaction.message.channel.id == COUNT_CHANNEL_ID and not user.bot:
            try:
                await reaction.remove(user)
            except:
                pass

    @bot.event
    async def on_message(message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Only process in the designated counting channel
        if message.channel.id != COUNT_CHANNEL_ID:
            return

        content = message.content.strip()

        # Try to parse as a number
        try:
            num = int(content)
        except ValueError:
            # Message contains text - delete it
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} ❌ Numbers only! No text/words allowed.",
                    delete_after=3
                )
            except discord.Forbidden:
                pass
            return

        # It's a number - check counting logic
        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)

        # Initialize guild data if not exists
        if guild_id not in count_data:
            count_data[guild_id] = {"channels": {}}
        
        channels = count_data[guild_id]["channels"]

        # Initialize channel count data if not exists
        if channel_id not in channels:
            channels[channel_id] = {
                "last_count": 0,
                "last_user_id": None
            }
            save_data(count_data)

        channel_count = channels[channel_id]
        last_count = channel_count["last_count"]
        expected = last_count + 1

        if num == expected:
            # Correct count
            channel_count["last_count"] = num
            channel_count["last_user_id"] = message.author.id
            save_data(count_data)
            # Bot auto-adds reaction for correct count
            try:
                await message.add_reaction("<:NepPath:1395694322061410334>")
            except:
                pass
        else:
            # Wrong count - delete and inform
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} ❌ Wrong number! Expected **{expected}**, not **{num}**. Last count was **{last_count}**.",
                    delete_after=5
                )
            except discord.Forbidden:
                pass

    print("Count system loaded.")
