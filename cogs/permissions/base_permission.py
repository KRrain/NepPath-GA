import discord
from discord.ext import commands
from setting_config import load_config, save_config, get_timestamp

class BasePermission(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_config()

    async def update_command_permissions(self):
        """Soft-hide slash commands for disabled roles + global lockdown."""
        for cmd in self.bot.tree.walk_commands():
            if isinstance(cmd, discord.app_commands.Command):
                perms = []
                for role in cmd.guild.roles if cmd.guild else []:
                    if role.permissions.administrator:
                        perms.append(discord.app_commands.CommandPermission(
                            id=role.id,
                            type=discord.app_commands.PermissionType.role,
                            permission=True
                        ))
                    elif self.config["global"]["disabled"] or self.config["roles"].get(str(role.id), {}).get("disabled"):
                        perms.append(discord.app_commands.CommandPermission(
                            id=role.id,
                            type=discord.app_commands.PermissionType.role,
                            permission=False
                        ))
                try:
                    await cmd.edit_permissions(permissions=perms)
                except Exception:
                    pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True

        # Global lockdown
        if self.config["global"].get("disabled"):
            await interaction.response.send_message(
                "🚨 Commands are currently disabled for everyone.",
                ephemeral=True
            )
            return False

        # Role-based
        user_roles = [str(role.id) for role in interaction.user.roles]
        if any(rid in self.config["roles"] and self.config["roles"][rid].get("disabled") for rid in user_roles):
            await interaction.response.send_message(
                "🚫 Your role is currently not allowed to use commands.",
                ephemeral=True
            )
            return False
        return True
