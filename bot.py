import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import aiohttp
import re
import json
from pathlib import Path
import io
from vtcs.embed import setup_embed_command
from vtcs.associated import setup as setup_assign_role
from vtcs.removed import setup as setup_remove_role
from vtcs.state import setup as setup_state
from vtcs.announcement import setup as setup_announcement, scrape_route_image
from vtcs.book import setup_book_command, BookSlotView, ApproveDenyView
from vtcs.marked import setup as setup_marked_command
from vtcs.status import setup_bot_present, restore_status
from vtcs.starboard import setup as setup_starboard
from vtcs.vtc_commands import setup_vtc
from vtcs.members import setup_members_command
from vtcs.upcoming import setup as setup_upcoming
from vtcs.help import setup as setup_help_command
from vtcs.server_lookup import setup as setup_server_lookup
from vtcs.Partnership import setup as setup_partnership, PartnershipView
from vtcs.license import setup as setup_license, LicenseView
from vtcs.traffic import setup as setup_traffic
from rdt.reminder import setup_reminder
from rdt.remind_config import setup_remind_config
from cogs.birthday import BirthdayView
from tkt.ticket import setup as setup_ticket, register_views as register_ticket_views
from tkt.role_req import setup as setup_role_req, RoleRequestView, RoleRequestAssignView

import config

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ================== CONFIG ==================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
    
setup_embed_command(bot)
setup_remove_role(bot.tree)
setup_assign_role(bot.tree)
setup_state(bot)
setup_announcement(bot)
setup_book_command(bot)
setup_marked_command(bot)
setup_bot_present(bot)
setup_starboard(bot)
setup_vtc(bot)
setup_members_command(bot)
setup_upcoming(bot)
setup_help_command(bot)
setup_server_lookup(bot)
setup_partnership(bot)
setup_license(bot)
setup_traffic(bot)
setup_ticket(bot)
setup_role_req(bot)

reminder_loop = setup_reminder(bot, bot.tree)
setup_remind_config(bot, bot.tree)

# /fix-all command: checks registration of key commands
@app_commands.command(name="fix-all", description="Check registration of all commands.")
async def fix_all(interaction: discord.Interaction):
    tree = interaction.client.tree
    commands_to_check = ["ping", "assign-role", "remove-role", "state", "starboard", "my_vtc", "members", "upcoming", "license"]
    status_lines = []
    for cmd_name in commands_to_check:
        found = any(cmd.name == cmd_name for cmd in tree.get_commands())
        status = "✅ Registered" if found else "❌ Missing"
        status_lines.append(f"/{cmd_name}: {status}")
    msg = "\n".join(status_lines)
    await interaction.response.send_message(f"**Command Registration Status:**\n{msg}", ephemeral=True)

bot.tree.add_command(fix_all)
# -------------------- UTILS --------------------
def is_staff(member: discord.Member):
    return any(role.id in config.STAFF_ROLE_ID for role in member.roles)

@bot.command(name="sync", description="Sync commands to the current guild immediately")
async def sync(ctx):
    if not is_staff(ctx.author):
        return await ctx.send("❌ You do not have permission to use this command.")
    
    msg = await ctx.send("🔄 Syncing commands...")
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await msg.edit(content="✅ Commands synced to this guild! They should appear immediately.")

class EditEmbedModal(discord.ui.Modal, title="Quick Edit Embed"):
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message
        embed = message.embeds[0]
        
        self.embed_title = discord.ui.TextInput(
            label="Title",
            default=embed.title or "",
            required=False,
            max_length=256
        )
        self.embed_desc = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.long,
            default=embed.description or "",
            required=False,
            max_length=4000
        )
        self.add_item(self.embed_title)
        self.add_item(self.embed_desc)

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0]
        embed.title = self.embed_title.value
        embed.description = self.embed_desc.value
        await self.message.edit(embed=embed)
        await interaction.response.send_message("✅ Embed updated successfully!", ephemeral=True)

# -------------------- COMMAND --------------------
@bot.tree.command(name="ping", description="Check bot latency (Staff only)")
async def ping(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latency:** {latency}ms",
        color=config.EMBED_COLOR,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="NepPath | Bot Status", icon_url=config.AVATAR_URL)
    await interaction.response.send_message(embed=embed)

@bot.tree.context_menu(name="Quick Edit")
async def quick_edit(interaction: discord.Interaction, message: discord.Message):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    
    if message.author != interaction.client.user:
        return await interaction.response.send_message("❌ I can only edit my own messages.", ephemeral=True)
    
    if not message.embeds:
        return await interaction.response.send_message("❌ This message does not contain an embed.", ephemeral=True)

    await interaction.response.send_modal(EditEmbedModal(message))

@bot.command(name="bot", description="Show bot details (README)")
async def bot_details(ctx):
    if not is_staff(ctx.author):
        return await ctx.send("❌ You do not have permission to use this command.")
    
    embed = discord.Embed(
        title="🚛 NepPath [Beta >> GA]",
        description="**NepPath GA** is a powerful, feature-rich Discord bot tailored for Virtual Trucking Companies (VTCs) operating on TruckersMP. It automates administrative tasks, streamlines event management, handles support tickets, and integrates directly with TruckersMP data.",
        color=config.EMBED_COLOR
    )
    
    features_text = (
        "**🎫 Advanced Ticket System**\n"
        "• Multi-Category Support (Invites, Partnership, Support, etc.)\n"
        "• Automated Event Fetching from TruckersMP\n"
        "• Staff Controls (Accept/Decline/Close) & Transcripts\n\n"
        "**📅 Event & Convoy Management**\n"
        "• `/announcement`: Professional event announcements with route scraping\n"
        "• `/book`: Slot booking system with visual status\n"
        "• `/mark`: Attendance marking for drivers\n"
        "• `/upcoming`: Search upcoming events\n\n"
        "**🚚 VTC Integration**\n"
        "• `/my_vtc`: Live VTC info from TruckersMP\n"
        "• `/members`: Member list sorted by rank\n"
        "• `/partnership`: Automated partnership requests\n\n"
        "**🎵 Entertainment & Utility**\n"
        "• `Music System`: `/np` with playlist support and per-server queues\n"
        "• `Birthday System`: Automated DOB registration and announcements\n"
        "• `Voice Master`: Dynamic 'Join to Create' temporary voice channels\n\n"
        "**🛠️ Administration & Moderation**\n"
        "• Role Management (`/assign-role`, `/remove-role`)\n"
        "• Message Cleaning (`/clean`, `/delete`)\n"
        "• Embed Builder & Quick Edit (Context Menu)\n"
        "• Bot Status (`/bot_present`)\n\n"
        "**🌟 Community Features**\n"
        "• Starboard, Server Info, Reminders"
    )
    embed.add_field(name="✨ Key Features", value=features_text, inline=False)
    
    commands_text = (
        "`/ticket` - Open ticket panel\n"
        "`/partnership` - Send partnership request\n"
        "`/announcement` - Post event announcement\n"
        "`/book` - Create slot booking embed\n"
        "`/mark` - Create attendance embed\n"
        "`/np` - Play music/playlists\n"
        "`/birthday-setup` - Initialize birthday registration\n"
        "`/upcoming` - Check events\n"
        "`/my_vtc` - Show VTC info\n"
        "`/license` - View driver profile card\n"
        "`/members` - List VTC members\n"
        "`/assign-role` - Assign role to user\n"
        "`/remove-role` - Remove role from user\n"
        "`/clean` / `/delete` - Delete messages\n"
        "`/embed` - Create custom embed\n"
        "`/bot_present` - Set bot status\n"
        "`/starboard` - Manage starboard\n"
        "`/server-info` - View server stats\n"
        "`/ping` - Check latency"
    )
    embed.add_field(name="📝 Command List", value=commands_text, inline=False)
    
    structure_text = (
        "```\n"
        "NepPath-Beta/\n"
        "├── bot.py\n"
        "├── config.py\n"
        "├── cogs/\n"
        "│   ├── clean.py\n"
        "│   └── permissions/\n"
        "│       ├── approve_role.py\n"
        "│       ├── disable_all_users.py\n"
        "│       ├── disable_role.py\n"
        "│       ├── enable_users.py\n"
        "│       └── status.py\n"
        "├── vtcs/\n"
        "│   ├── Partnership.py\n"
        "│   ├── announcement.py\n"
        "│   ├── associated.py\n"
        "│   ├── book.py\n"
        "│   ├── embed.py\n"
        "│   ├── help.py\n"
        "│   ├── marked.py\n"
        "│   ├── members.py\n"
        "│   ├── license.py\n"
        "│   ├── removed.py\n"
        "│   ├── server_lookup.py\n"
        "│   ├── starboard.py\n"
        "│   ├── state.py\n"
        "│   ├── status.py\n"
        "│   ├── upcoming.py\n"
        "│   └── vtc_commands.py\n"
        "└── data/\n"
        "    ├── bookings.json\n"
        "    ├── leaderboard.json\n"
        "    ├── starboard_config.json\n"
        "    ├── tickets.json\n"
        "    └── vtc_role_data.json\n"
        "```"
    )
    embed.add_field(name="📂 Project Structure", value=structure_text, inline=False)
    
    updates_text = (
        "• **New Music System**: High-quality audio with YouTube/Playlist support.\n"
        "• **Birthday Registry**: Automated DOB tracking and beautiful banner announcements.\n"
        "• **Voice Master**: Dynamic VCs with automated setup prompts.\n"
        "• **Ticket Privacy**: Enhanced permission overwrites for management tickets.\n"
        "• **Management Categories**: Dedicated ticket routing for HR/CEO/Founder requests."
    )
    embed.add_field(name="🆕 Recent Updates", value=updates_text, inline=False)
    
    embed.add_field(name="🤝 Developer", value="Developed by **Lucifer_NP [ Kabi ]** for **NepPath**.", inline=False)
    
    thanks_text = "<@536124118999760906>, <@1395829670297210920>, <@939726500884803627>, <@1364956471766417448> / and **NepPath all members**"
    embed.add_field(name="❤️ Special Thanks", value=thanks_text, inline=False)

    embed.set_footer(text="NepPath | General availability | Bot Information", icon_url=config.AVATAR_URL)
    
    await ctx.send(embed=embed)

async def setup_permission_cogs(bot: commands.Bot):
    """Loads all cogs from the cogs/permissions directory."""
    permissions_cog_dir = Path(__file__).parent / "cogs" / "permissions"
    for filepath in permissions_cog_dir.glob("*.py"):
        if filepath.name in ("__init__.py", "base_permission.py"):
            continue
        
        # Convert file path to dot-separated extension format
        extension = f"cogs.permissions.{filepath.stem}"
        try:
            await bot.load_extension(extension)
            print(f"✅ Loaded permission cog: {extension}")
        except Exception as e:
            print(f"❌ Failed to load permission cog {extension}: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"⚠️ Command Error: {error}")

# -------------------- READY --------------------
@bot.event
async def on_ready():
    await setup_permission_cogs(bot)
    try:
        await bot.load_extension("cogs.clean")
        print("✅ Loaded extension: cogs.clean")
    except Exception as e:
        print(f"❌ Failed to load extension cogs.clean: {e}")
    try:
        await bot.load_extension("cogs.birthday")
        print("✅ Loaded extension: cogs.birthday")
    except Exception as e:
        print(f"❌ Failed to load extension cogs.birthday: {e}")
    try:
        await bot.load_extension("cogs.voice")
        print("✅ Loaded extension: cogs.voice")
    except Exception as e:
        print(f"❌ Failed to load extension cogs.voice: {e}")
    try:
        await bot.load_extension("cogs.music")
        print("✅ Loaded extension: cogs.music")
    except Exception as e:
        print(f"❌ Failed to load extension cogs.music: {e}")

    if not reminder_loop.is_running():
        reminder_loop.start()

    # Register persistent views so buttons work after restart
    register_ticket_views(bot)
    bot.add_view(BookSlotView())
    bot.add_view(ApproveDenyView())
    bot.add_view(PartnershipView())
    bot.add_view(RoleRequestView())
    bot.add_view(BirthdayView())
    bot.add_view(RoleRequestAssignView())
    bot.add_view(LicenseView())

    if hasattr(config, "GUILD_ID") and config.GUILD_ID != 0:
        guild = discord.Object(id=config.GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"✅ Commands synced to Guild ID: {config.GUILD_ID}")
        # Debug: Print synced commands to console
        cmds = [c.name for c in bot.tree.get_commands(guild=guild)]
        print(f"📋 Active Commands: {', '.join(cmds)}")
        # Clear global commands on Discord ONLY (Keep in memory for !sync)
        # This removes duplicates without breaking the internal tree
        await bot.http.bulk_upsert_global_commands(bot.application_id, [])
    else:
        await bot.tree.sync()
    await restore_status(bot)
    print(f"✅ Logged in as {bot.user}")
    
 
bot.run(TOKEN)
