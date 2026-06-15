import discord
from discord.ext import commands
from discord import app_commands
from .base_permission import BasePermission
from setting_config import save_config, get_timestamp

class ApproveRole(BasePermission):
    @app_commands.command(name="approve_role", description="Enable all commands for a role")
    @app_commands.checks.has_permissions(administrator=True)
    async def approve_role(self, interaction: discord.Interaction, role: discord.Role, reason: str = "No reason"):
        rid = str(role.id)
        if rid in self.config["roles"]:
            self.config["roles"][rid]["disabled"] = False
            self.config["roles"][rid]["reason"] = reason
            self.config["roles"][rid]["timestamp"] = get_timestamp()
            save_config(self.config)
            await self.update_command_permissions()
            await interaction.response.send_message(
                f"✅ All commands enabled for role **{role.name}**.\nReason: {reason}", ephemeral=True
            )
        else:
            await interaction.response.send_message("Role is not disabled.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ApproveRole(bot))
