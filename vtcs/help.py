import discord
from discord import app_commands
from discord.ext import commands
import config

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Home", emoji="🏠", description="General information"),
            discord.SelectOption(label="Tickets", emoji="🎫", description="Ticket system commands"),
            discord.SelectOption(label="Events", emoji="📅", description="Event & Booking commands"),
            discord.SelectOption(label="VTC & Members", emoji="🚚", description="VTC information commands"),
            discord.SelectOption(label="Management", emoji="🛡️", description="Staff management commands"),
            discord.SelectOption(label="Utility", emoji="🛠️", description="Utility & Starboard commands"),
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        embed = discord.Embed(color=config.EMBED_COLOR)
        embed.set_footer(text=config.FOOTER_TEXT, icon_url=config.AVATAR_URL)

        if val == "Home":
            embed.title = "🤖 NepPath Bot Help"
            embed.description = (
                "Welcome to the help menu! Use the dropdown below to navigate through command categories.\n\n"
                "**Categories:**\n"
                "🎫 **Tickets** - Support & Event Invites\n"
                "📅 **Events** - Announcements & Booking\n"
                "🚚 **VTC** - Company Info & Members\n"
                "🛡️ **Management** - Roles & Reminders\n"
                "🛠️ **Utility** - Status & Tools\n\n"
                "__**Developer**__\n"
                "Copyright NepPath, Developed By Lucifer_NP [ Kabi ]"
            )
        
        elif val == "Tickets":
            embed.title = "🎫 Ticket Commands"
            embed.add_field(name="/ticket", value="Open the ticket creation menu (Staff Only).", inline=False)
            embed.add_field(name="Features", value="Invite Us, Partnership, Support, Transcripts, Claiming.", inline=False)

        elif val == "Events":
            embed.title = "📅 Event Commands"
            embed.add_field(name="/announcement [channel]", value="Create a TruckersMP event announcement.", inline=False)
            embed.add_field(name="/book [channel]", value="Create a slot booking embed.", inline=False)
            embed.add_field(name="/mark [link] [channel]", value="Create an attendance marking embed.", inline=False)
            embed.add_field(name="/upcoming", value="Check upcoming VTC events.", inline=False)

        elif val == "VTC & Members":
            embed.title = "🚚 VTC Commands"
            embed.add_field(name="/my_vtc", value="Display VTC information.", inline=False)
            embed.add_field(name="/members", value="List VTC members sorted by rank.", inline=False)

        elif val == "Management":
            embed.title = "🛡️ Management Commands"
            embed.add_field(name="/assign-role [user] [role]", value="Assign a role (Authorized only).", inline=False)
            embed.add_field(name="/remove-role [user] [role]", value="Remove a role (Authorized only).", inline=False)
            embed.add_field(name="/embed [role]", value="Create custom embeds.", inline=False)
            embed.add_field(name="/reminder", value="Set a scheduled reminder.", inline=False)
            embed.add_field(name="/remind_config", value="Manage active reminders.", inline=False)

        elif val == "Utility":
            embed.title = "🛠️ Utility Commands"
            embed.add_field(name="/ping", value="Check bot latency.", inline=False)
            embed.add_field(name="/state", value="View bot statistics.", inline=False)
            embed.add_field(name="/server-info", value="View server details.", inline=False)
            embed.add_field(name="/bot_present", value="Set bot status.", inline=False)
            embed.add_field(name="/starboard config", value="View starboard settings.", inline=False)
            embed.add_field(name="/starboard leaderboard", value="View top starred messages.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())

def setup(bot: commands.Bot):
    @bot.tree.command(name="help", description="Show list of commands")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 NepPath Bot Help",
            description="Select a category below to view commands.",
            color=config.EMBED_COLOR
        )
        embed.set_footer(text=config.FOOTER_TEXT, icon_url=config.AVATAR_URL)
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)