import discord
from discord import app_commands
from discord.ui import View, Select, Modal, TextInput, Button
import os
import sys
from datetime import datetime

# Ensure we can import from the sibling module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
from rdt.reminder import reminders, save_data, is_staff

def setup_remind_config(bot: discord.Client, tree: app_commands.CommandTree):
    GUILD_ID = config.GUILD_ID

    def get_common_embed(title, description):
        """Helper to create consistent embeds with avatar, footer, timestamp."""
        embed = discord.Embed(title=title, description=description, color=config.EMBED_COLOR)
        embed.set_author(name=config.FOOTER_TEXT, icon_url=config.AVATAR_URL)
        embed.set_footer(text=f"{config.FOOTER_TEXT} || {datetime.now().strftime('%Y-%m-%d %H:%M')}", icon_url=config.AVATAR_URL)
        return embed

    @app_commands.command(
        name="remind_config",
        description="Manage reminders: Edit, View, or Delete"
    )
    async def remind_config_command(interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.", ephemeral=True
            )
            return

        if not reminders:
            await interaction.response.send_message(
                "❌ No active reminders to configure.", ephemeral=True
            )
            return

        def get_options():
            options = []
            for i, r in enumerate(reminders):
                label = f"[{r.get('timestamp', 'N/A')}] {r.get('title', 'No Title')}"
                label = label[:100]
                description = r.get("description", "")[:100]
                options.append(discord.SelectOption(label=label, description=description or "No description", value=str(i)))
            return options[:25]

        # ---------------- View Class ----------------
        class ConfigView(View):
            def __init__(self):
                super().__init__(timeout=180)
                self.add_selects()

            def add_selects(self):
                options = get_options()
                if not options:
                    options = [discord.SelectOption(label="No reminders", value="-1")]
                
                # 1. Edit Selection
                self.select_edit = Select(
                    placeholder="✏️ Select to Edit...",
                    options=options,
                    custom_id="select_edit",
                    row=0
                )
                self.select_edit.callback = self.on_edit_select
                self.add_item(self.select_edit)

                # 2. View Selection
                self.select_view = Select(
                    placeholder="👀 Select to View...",
                    options=options,
                    custom_id="select_view",
                    row=1
                )
                self.select_view.callback = self.on_view_select
                self.add_item(self.select_view)

                # 3. Delete Selection
                self.select_delete = Select(
                    placeholder="🗑️ Select to Delete...",
                    options=options,
                    custom_id="select_delete",
                    row=2
                )
                self.select_delete.callback = self.on_delete_select
                self.add_item(self.select_delete)

            async def refresh(self):
                self.clear_items()
                self.add_selects()
                try:
                    await interaction.edit_original_response(view=self)
                except:
                    pass

            async def on_edit_select(self, select_interaction: discord.Interaction):
                values = select_interaction.data.get("values", [])
                await self.refresh()

                try:
                    index = int(values[0])
                    if index >= len(reminders): raise IndexError
                    selected_reminder = reminders[index]
                except (ValueError, IndexError):
                    await select_interaction.response.send_message("❌ Reminder not found.", ephemeral=True)
                    return

                # Popup Editing Modal
                view_instance = self
                class EditModal(Modal, title="Edit Reminder"):
                    title_input = TextInput(label="Title", default=selected_reminder.get("title", ""), max_length=100)
                    description_input = TextInput(label="Description", default=selected_reminder.get("description", ""), style=discord.TextStyle.paragraph)
                    datetime_input = TextInput(label="Date (YYYY-MM-DD HH:MM)", default=selected_reminder.get("timestamp", ""))

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            datetime.strptime(self.datetime_input.value, "%Y-%m-%d %H:%M")
                        except ValueError:
                            await modal_interaction.response.send_message("❌ Invalid date format.", ephemeral=True)
                            return

                        selected_reminder["title"] = self.title_input.value
                        selected_reminder["description"] = self.description_input.value
                        selected_reminder["timestamp"] = self.datetime_input.value
                        save_data(reminders)

                        embed = get_common_embed("✅ Reminder Updated", f"Updated: {self.title_input.value}")
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                        await view_instance.refresh()

                await select_interaction.response.send_modal(EditModal())

            async def on_view_select(self, select_interaction: discord.Interaction):
                values = select_interaction.data.get("values", [])
                await self.refresh()

                try:
                    index = int(values[0])
                    if index >= len(reminders): raise IndexError
                    r = reminders[index]
                except (ValueError, IndexError):
                    await select_interaction.response.send_message("❌ Reminder not found.", ephemeral=True)
                    return

                channel_id = r.get("channel_id")
                role_ids = r.get("roles", [])
                images = r.get("images", [])
                channel_mention = f"<#{channel_id}>" if channel_id else "Unknown"
                roles_mention = ", ".join(f"<@&{rid}>" for rid in role_ids) if role_ids else "None"

                desc = (
                    f"**Title:** {r.get('title')}\n"
                    f"**Time:** {r.get('timestamp')}\n"
                    f"**Channel:** {channel_mention}\n"
                    f"**Roles:** {roles_mention}\n"
                    f"**Images:** {len(images)}\n\n"
                    f"**Description:**\n{r.get('description')}"
                )
                
                embed = get_common_embed("📅 Reminder Details", desc)
                
                embeds = [embed]
                if images:
                    embed.set_image(url=images[0])
                    for img_url in images[1:]:
                        img_embed = discord.Embed(color=config.EMBED_COLOR)
                        img_embed.set_image(url=img_url)
                        embeds.append(img_embed)

                await select_interaction.response.send_message(embeds=embeds, ephemeral=False) # "send embed same channel"

            async def on_delete_select(self, select_interaction: discord.Interaction):
                values = select_interaction.data.get("values", [])
                await self.refresh()

                try:
                    index = int(values[0])
                    if index >= len(reminders): raise IndexError
                    r = reminders[index]
                except (ValueError, IndexError):
                    await select_interaction.response.send_message("❌ Reminder not found.", ephemeral=True)
                    return

                # Confirmation View
                view_instance = self
                class ConfirmDeleteView(View):
                    def __init__(self):
                        super().__init__(timeout=60)

                    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
                    async def confirm(self, btn_interaction: discord.Interaction, button: Button):
                        if r in reminders:
                            reminders.remove(r)
                            save_data(reminders)
                            embed = get_common_embed("🗑️ Deleted", f"Reminder '{r.get('title')}' has been deleted.")
                            await btn_interaction.response.send_message(embed=embed, ephemeral=True)
                            
                            # Disable buttons
                            for child in self.children:
                                child.disabled = True
                            await select_interaction.edit_original_response(view=self)
                            await view_instance.refresh()
                        else:
                            await btn_interaction.response.send_message("❌ Already deleted.", ephemeral=True)

                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, btn_interaction: discord.Interaction, button: Button):
                        embed = get_common_embed("❌ Cancelled", "Deletion cancelled.")
                        await btn_interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # Disable buttons
                        for child in self.children:
                            child.disabled = True
                        await select_interaction.edit_original_response(view=self)

                embed = get_common_embed("⚠️ Confirm Deletion", f"Are you sure you want to delete **{r.get('title')}**?")
                await select_interaction.response.send_message(embed=embed, view=ConfirmDeleteView(), ephemeral=True)

        embed = get_common_embed("⚙️ Reminder Configuration", "Select an action below to Edit, View, or Delete reminders.")
        await interaction.response.send_message(embed=embed, view=ConfigView(), ephemeral=True)

    # Register command
    if GUILD_ID:
        tree.add_command(remind_config_command, guild=discord.Object(id=GUILD_ID))
    else:
        tree.add_command(remind_config_command)