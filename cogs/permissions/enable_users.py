import discord
from discord.ext import commands
from discord import app_commands
from .base_permission import BasePermission
from setting_config import save_config

class EnableUsers(BasePermission):
    @app_commands.command(name="enable_users", description="Enable all users globally")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_users(self, interaction: discord.Interaction):
        self.config["global"]["disabled"] = False
        save_config(self.config)
        await self.update_command_permissions()
        await interaction.response.send_message(
            "✅ All users are now enabled. Role-based disables remain.", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(EnableUsers(bot))
