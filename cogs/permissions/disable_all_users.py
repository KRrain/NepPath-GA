import discord
from discord.ext import commands
from discord import app_commands
from .base_permission import BasePermission
from setting_config import save_config, get_timestamp

class DisableAllUsers(BasePermission):
    @app_commands.command(name="disable_all_users", description="Disable all commands globally")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_all_users(self, interaction: discord.Interaction, hide: bool = True, reason: str = "No reason"):
        self.config["global"] = {
            "disabled": True,
            "hide": hide,
            "reason": reason,
            "timestamp": get_timestamp()
        }
        save_config(self.config)
        await self.update_command_permissions()
        await interaction.response.send_message(
            f"🚨 Global lockdown enabled.\nReason: {reason}\nHide commands: {hide}", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(DisableAllUsers(bot))
