import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import config

MAX_INPUT_LENGTH = 4000
EMBED_DESCRIPTION_LIMIT = 4096


class EmbedModal(discord.ui.Modal, title="Create an Embed"):

    def __init__(self, roles: list, channel: discord.TextChannel):
        super().__init__()
        self.roles = roles
        self.channel = channel

        # ===== 5-input limit =====
        self.embed_title = discord.ui.TextInput(
            label="Embed Title (Main)",
            required=False,
            max_length=256,
            placeholder="Main embed title"
        )

        self.description = discord.ui.TextInput(
            label=f"Description (Main)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=MAX_INPUT_LENGTH,
            placeholder="Main embed description"
        )

        self.image1 = discord.ui.TextInput(
            label="Image 1 (Main Embed)",
            required=False,
            placeholder="https://example.com/image.png"
        )

        self.image2 = discord.ui.TextInput(
            label="Image 2 (Embed 2)",
            required=False
        )

        self.image3 = discord.ui.TextInput(
            label="Image 3 (Embed 3)",
            required=False
        )

        self.add_item(self.embed_title)
        self.add_item(self.description)
        self.add_item(self.image1)
        self.add_item(self.image2)
        self.add_item(self.image3)

        # Optional button URL handled separately (after modal) if needed

    async def on_submit(self, interaction: discord.Interaction):
        desc_text = self.description.value or ""
        if len(desc_text) > EMBED_DESCRIPTION_LIMIT:
            desc_text = desc_text[:EMBED_DESCRIPTION_LIMIT]

        embeds = []

        # ===== MAIN EMBED =====
        main_embed = discord.Embed(
            title=self.embed_title.value or " ",
            description=desc_text or None,
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        if self.image1.value:
            main_embed.set_image(url=self.image1.value)
        main_embed.set_footer(text=config.FOOTER_TEXT, icon_url=config.FOOTER_ICON)
        embeds.append(main_embed)

        # ===== EMBED 2 =====
        if self.image2.value:
            embed2 = discord.Embed(color=config.EMBED_COLOR)
            embed2.set_image(url=self.image2.value)
            embed2.set_footer(text=config.FOOTER_TEXT, icon_url=config.FOOTER_ICON)
            embeds.append(embed2)

        # ===== EMBED 3 =====
        if self.image3.value:
            embed3 = discord.Embed(color=config.EMBED_COLOR)
            embed3.set_image(url=self.image3.value)
            embed3.set_footer(text=config.FOOTER_TEXT, icon_url=config.FOOTER_ICON)
            embeds.append(embed3)

        # ===== Send main message =====
        await self.channel.send(
            content=" ".join(r.mention for r in self.roles),
            embeds=embeds
        )

        await interaction.response.send_message(
            "✅ Main embed sent successfully!",
            ephemeral=True
        )


class RoleSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select roles to mention", min_values=1, max_values=25)
    async def select_roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        modal = EmbedModal(select.values, interaction.channel)
        await interaction.response.send_modal(modal)


# ================== SLASH COMMAND ==================
def setup_embed_command(bot: commands.Bot):

    @bot.tree.command(
        name="embed",
        description="Create a main embed with additional embeds"
    )
    async def embed(interaction: discord.Interaction):
        view = RoleSelectionView()
        await interaction.response.send_message("Please select the roles you want to mention:", view=view, ephemeral=True)
