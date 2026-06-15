import discord
from discord.ext import commands
from discord import app_commands
from .base_permission import BasePermission
from setting_config import save_config, get_timestamp

class DisableRole(BasePermission):
    @app_commands.command(name="disable_role", description="Disable all commands for a role")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_role(self, interaction: discord.Interaction, role: discord.Role, reason: str = "No reason"):
        rid = str(role.id)
        self.config["roles"][rid] = {
            "disabled": True,
            "reason": reason,
            "timestamp": get_timestamp()
        }
        save_config(self.config)
        await self.update_command_permissions()
        await interaction.response.send_message(
            f"❌ All commands disabled for role **{role.name}**.\nReason: {reason}", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(DisableRole(bot))
