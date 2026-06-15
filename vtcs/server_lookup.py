import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import config

def setup(bot: commands.Bot):
    
    # ---------------- CURRENT SERVER INFO ----------------
    @bot.tree.command(name="server-info", description="Get information about this server")
    async def server_info(interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)

        embed = discord.Embed(
            title=f"ℹ️ Server Info: {guild.name}",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="👥 Members", value=f"{guild.member_count}", inline=True)
        
        created_at = guild.created_at.strftime("%B %d, %Y")
        embed.add_field(name="📅 Created On", value=created_at, inline=True)
        
        embed.add_field(name="🚀 Boosts", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        embed.add_field(name="💬 Channels", value=f"Text: {text_channels} | Voice: {voice_channels}", inline=True)
        
        embed.add_field(name="🎭 Roles", value=f"{len(guild.roles)}", inline=True)
        embed.add_field(name="😀 Emojis", value=f"{len(guild.emojis)}", inline=True)

        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)