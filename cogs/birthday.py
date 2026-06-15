import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import config
from datetime import datetime
from pathlib import Path

def load_birthdays():
    if not config.BIRTHDAY_FILE.exists():
        return {}
    try:
        with open(config.BIRTHDAY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_birthdays(data):
    config.BIRTHDAY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.BIRTHDAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class BirthdayModal(discord.ui.Modal, title="Fill Your Date of Birth"):
    dob = discord.ui.TextInput(
        label="Date of Birth (DD/MM/YYYY)",
        placeholder="e.g. 15/05/2000",
        min_length=10,
        max_length=10,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        val = self.dob.value.strip()
        try:
            # Validate format dd/mm/yyyy
            datetime.strptime(val, "%d/%m/%Y")
        except ValueError:
            return await interaction.response.send_message("❌ Invalid format! Please use **DD/MM/YYYY** (e.g., 15/05/2000).", ephemeral=True)

        data = load_birthdays()
        data[str(interaction.user.id)] = val
        save_birthdays(data)

        await interaction.response.send_message(f"✅ Your birthday has been saved as **{val}**!", ephemeral=True)

class BirthdayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fill DOB", style=discord.ButtonStyle.primary, emoji="🎂", custom_id="birthday_fill_btn")
    async def fill_dob(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BirthdayModal())

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        await self.bot.wait_until_ready()
        now = datetime.utcnow()
        day_month = now.strftime("%d/%m")
        
        data = load_birthdays()
        guild = self.bot.get_guild(config.GUILD_ID)
        if not guild: return
        
        channel = guild.get_channel(config.BIRTHDAY_ANNOUNCE_CHANNEL_ID)
        if not channel: return

        for user_id, dob_str in data.items():
            # dob_str is dd/mm/yyyy, we check if starts with dd/mm
            if dob_str.startswith(day_month):
                try:
                    member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                    if member:
                        embed = self.create_birthday_embed(member)
                        await channel.send(content=f"🎉 Happy Birthday {member.mention}! 🎂", embed=embed)
                except:
                    continue

    def create_birthday_embed(self, user: discord.Member | discord.User):
        embed = discord.Embed(
            title="🎂 Happy Birthday! 🥳",
            description=(
                f"🎊 @everyone Today is a very special day! 🎉\n\n"
                f"Let's all wish {user.mention} a very **Happy Birthday**! 🎈✨\n\n"
                f"May your day be filled with joy, happiness, and lots of success! 🚛💨❤️"
            ),
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_image(url=config.BIRTHDAY_BANNER_URL)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="NepPath | Birthday Wishes", icon_url=config.AVATAR_URL)
        return embed

    @app_commands.command(name="dobtest", description="Demo view for birthday announcement")
    async def dobtest(self, interaction: discord.Interaction):
        embed = self.create_birthday_embed(interaction.user)
        await interaction.response.send_message(content="🎉 This is how a birthday announcement looks:", embed=embed)

    @app_commands.command(name="birthday-setup", description="Post the DOB fill embed (Staff Only)")
    async def setup_dob(self, interaction: discord.Interaction):
        if not any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)

        embed = discord.Embed(
            title="🎂 Register Your Birthday",
            description=(
                "Click the button below to register your Date of Birth!\n\n"
                "📅 **Format:** `DD/MM/YYYY`\n"
                "🎁 **Benefit:** Get a special shoutout on your birthday!\n\n"
                "🔒 Only your day and month will be announced."
            ),
            color=config.EMBED_COLOR
        )
        embed.set_footer(text="NepPath | Birthday System", icon_url=config.AVATAR_URL)
        await interaction.channel.send(embed=embed, view=BirthdayView())
        await interaction.response.send_message("✅ Birthday setup message sent!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Birthday(bot))