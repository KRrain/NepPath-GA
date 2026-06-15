import discord
from discord.ext import commands
from discord import app_commands
import config

class RenameVCModal(discord.ui.Modal, title="Set VC Channel Name"):
    name = discord.ui.TextInput(
        label="Channel Name",
        placeholder="Enter your VC name here...",
        min_length=2,
        max_length=50,
        required=True
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.edit(name=self.name.value)
        await interaction.response.send_message(f"✅ Channel renamed to: **{self.name.value}**", ephemeral=True)

class VoiceControlView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel, owner: discord.Member):
        super().__init__(timeout=None)
        self.channel = channel
        self.owner = owner

    @discord.ui.button(label="Set Channel Name", style=discord.ButtonStyle.primary, emoji="📝", custom_id="vc_rename_btn")
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message("❌ Only the channel creator can rename this VC.", ephemeral=True)
        
        await interaction.response.send_modal(RenameVCModal(self.channel))

class VoiceMaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {} # {channel_id: owner_id}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. Handle Joining Master VC
        if after.channel and after.channel.id == config.VOICE_MASTER_CHANNEL_ID:
            guild = member.guild
            category = after.channel.category
            
            # Create temporary channel
            new_channel = await guild.create_voice_channel(
                name=f"⌛ Name Needed - {member.display_name}",
                category=category,
                bitrate=after.channel.bitrate,
                user_limit=after.channel.user_limit
            )
            
            # Move member to the new channel
            await member.move_to(new_channel)
            self.temp_channels[new_channel.id] = member.id
            
            # Send prompt to set name in the voice channel's text chat
            embed = discord.Embed(
                title="🎙️ New Voice Channel Created",
                description=(
                    f"Welcome {member.mention}!\n\n"
                    "**ACTION REQUIRED:** Please click the button below to set your channel name.\n\n"
                    "⚠️ *Discord requires a button click to show the name popup.*"
                ),
                color=config.EMBED_COLOR
            )
            embed.set_footer(text="NepPath | Voice Master", icon_url=config.AVATAR_URL)
            
            view = VoiceControlView(new_channel, member)
            await new_channel.send(content=member.mention, embed=embed, view=view)

        # 2. Handle Deleting Empty Channels
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="Temporary VC empty.")
                    del self.temp_channels[before.channel.id]
                except:
                    pass

    @app_commands.command(name="vc-rename", description="Rename your current voice channel")
    async def vc_rename(self, interaction: discord.Interaction, name: str):
        """Manual command to rename if the button isn't used."""
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ You are not in a voice channel.", ephemeral=True)
        
        channel_id = interaction.user.voice.channel.id
        if channel_id not in self.temp_channels:
            return await interaction.response.send_message("❌ This is not a temporary voice channel.", ephemeral=True)
            
        if self.temp_channels[channel_id] != interaction.user.id:
            return await interaction.response.send_message("❌ You do not own this channel.", ephemeral=True)

        await interaction.user.voice.channel.edit(name=name)
        await interaction.response.send_message(f"✅ Channel renamed to: **{name}**", ephemeral=True)

async def setup(bot):
    cog = VoiceMaster(bot)
    await bot.add_cog(cog)
    # Register the view for persistence
    # Note: Because the view depends on the specific channel object, 
    # full persistence across restarts for existing VCs requires a more complex DB setup.
    # For now, it works for all newly created channels.