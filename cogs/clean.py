import discord
from discord.ext import commands
from discord import app_commands
import config

class Clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clean", description="Delete a specified number of messages")
    @app_commands.describe(amount="Number of messages to delete")
    async def clean(self, interaction: discord.Interaction, amount: int):
        # Check permissions: Manage Messages or Staff Role
        is_staff = any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles)
        if not is_staff and not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

        if amount < 1:
            return await interaction.response.send_message("❌ Please enter a number greater than 0.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"✅ Deleted {len(deleted)} messages.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error deleting messages: {e}", ephemeral=True)

    @app_commands.command(name="delete", description="Delete specific messages by IDs")
    @app_commands.describe(message_ids="Paste message IDs separated by space")
    async def delete(self, interaction: discord.Interaction, message_ids: str):
        # Check permissions: Manage Messages or Staff Role
        is_staff = any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles)
        if not is_staff and not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        ids = message_ids.replace(",", " ").split()
        deleted_count = 0
        failed_count = 0

        for msg_id in ids:
            if not msg_id.isdigit():
                continue
            try:
                msg = await interaction.channel.fetch_message(int(msg_id))
                await msg.delete()
                deleted_count += 1
            except Exception:
                failed_count += 1
        
        await interaction.followup.send(f"✅ Deleted {deleted_count} messages. (Failed: {failed_count})", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Clean(bot))