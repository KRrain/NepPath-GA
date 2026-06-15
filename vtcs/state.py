import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
from pathlib import Path
import config

# Store bot start time
bot_start_time = None


def is_staff(member: discord.Member):
    return any(role.id in config.STAFF_ROLE_ID for role in member.roles)


def get_ticket_count():
    """Get total number of tickets from records"""
    if not config.TICKET_RECORD_FILE.exists():
        return 0
    try:
        with config.TICKET_RECORD_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return len(data) if data else 0
    except Exception:
        return 0


def format_uptime(delta):
    """Format timedelta into readable string"""
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)


def setup(bot: commands.Bot):
    global bot_start_time
    bot_start_time = datetime.utcnow()

    @bot.tree.command(
        name="state",
        description="Check bot status and statistics (Staff only)"
    )
    async def state(interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.", 
                ephemeral=True
            )

        # Calculate stats
        latency = round(bot.latency * 1000)
        guild_count = len(bot.guilds)
        member_count = sum(g.member_count for g in bot.guilds if g.member_count)
        ticket_count = get_ticket_count()
        
        # Calculate uptime
        uptime_str = "N/A"
        if bot_start_time:
            uptime = datetime.utcnow() - bot_start_time
            uptime_str = format_uptime(uptime)

        embed = discord.Embed(
            title="📊 Bot Status",
            description="Current bot statistics and status information.",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="🏓 Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="🌐 Servers", value=f"`{guild_count}`", inline=True)
        embed.add_field(name="👥 Total Members", value=f"`{member_count}`", inline=True)
        embed.add_field(name="🎫 Total Tickets", value=f"`{ticket_count}`", inline=True)
        embed.add_field(name="🤖 Bot", value=f"`{bot.user.name}`", inline=True)
        
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else config.AVATAR_URL)
        embed.set_footer(text="NepPath | Bot Status", icon_url=config.AVATAR_URL)

        await interaction.response.send_message(embed=embed)
