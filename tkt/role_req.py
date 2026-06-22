import discord
from discord import app_commands
from discord.ext import commands
import config
import re
import asyncio
import io
import random

class RoleAssignmentModal(discord.ui.Modal, title="Finalize Assignment"):
    new_nick = discord.ui.TextInput(label="Change Nickname", placeholder="Enter new nickname", required=True, max_length=32)

    def __init__(self, message: discord.Message, user_id: int, view: discord.ui.View, role: discord.Role):
        super().__init__()
        self.message = message
        self.user_id = user_id
        self.view = view
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild = interaction.guild
        member = None
        try:
            member = await guild.fetch_member(self.user_id)
        except discord.NotFound:
            return await interaction.followup.send("❌ User not found in server.", ephemeral=True)

        # 1. Change Nickname
        old_nick = member.display_name
        try:
            await member.edit(nick=self.new_nick.value, reason=f"Role Request Approved by {interaction.user}")
            await interaction.followup.send(f"✅ Nickname changed: `{old_nick}` -> `{self.new_nick.value}`", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Failed to change nickname (Missing Permissions).", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error changing nickname: {e}", ephemeral=True)

        # 2. Assign Role (Using selected role)
        role_to_assign = self.role

        if role_to_assign:
            try:
                await member.add_roles(role_to_assign, reason=f"Role Request Approved by {interaction.user}")
                await interaction.followup.send(f"✅ Assigned role: {role_to_assign.mention}", ephemeral=True)

                dm_embed = discord.Embed(
                    title="✅ Role Request Update",
                    description=f"Your role request has been approved in **{guild.name}**. You have been assigned the **{role_to_assign.name}** role.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                dm_embed.add_field(name="Assigned By", value=interaction.user.mention, inline=True)
                dm_embed.add_field(name="Nickname", value=f"`{self.new_nick.value}`", inline=True)
                dm_embed.set_footer(text="NepPath | Role Request", icon_url=config.AVATAR_URL)

                # Check for server link in parent view to include in DM
                dm_view = None
                for child in self.view.children:
                    if isinstance(child, discord.ui.Button) and child.url:
                        dm_view = discord.ui.View()
                        dm_view.add_item(discord.ui.Button(label="Join Server", style=discord.ButtonStyle.link, url=child.url))
                        break

                try:
                    await member.send(embed=dm_embed, view=dm_view)
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Could not DM the user (DMs closed).", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(f"⚠️ Failed to assign role {role_to_assign.mention} (Missing Permissions).", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"⚠️ Error assigning role: {e}", ephemeral=True)

        # 3. Update Embed
        embed = self.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Assigned By", value=interaction.user.mention, inline=False)
        if role_to_assign:
             embed.add_field(name="Role Given", value=role_to_assign.mention, inline=False)
        
        # Disable button
        for child in self.view.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "role_req_assign_btn":
                child.disabled = True
                child.label = "Assigned ✅"
        
        await self.message.edit(embed=embed, view=self.view)

class AssignRoleSelectView(discord.ui.View):
    def __init__(self, message: discord.Message, user_id: int, parent_view: discord.ui.View):
        super().__init__(timeout=120)
        self.message = message
        self.user_id = user_id
        self.parent_view = parent_view

        # Define roles dynamically to ensure latest config values are used
        role_store = {
            "Driver": getattr(config, "DRIVER_ROLE_ID", None),
            "Partner": getattr(config, "PARTNER_ROLE_ID", None),
            "Event Manager": getattr(config, "EVENT_MANAGER_ROLE_ID", None),
            "HR Team": getattr(config, "HR_ROLE_ID", None),
            "Manager": getattr(config, "MANAGER_ROLE_ID", None),
            "Recruitment": getattr(config, "RECRUITMENT_ROLE_ID", None),
            "CEO": getattr(config, "CEO_ROLE_ID", None),
            "Founder": getattr(config, "FOUNDER_ROLE_ID", None),
            "Community Members": getattr(config, "COMMUNITY_MEMBERS_ROLE_ID", None),
            "Media Team": getattr(config, "MEDIA_ROLE_ID", None),
        }

        options = []
        for name, role_id in role_store.items():
            if role_id:
                options.append(discord.SelectOption(label=name, value=str(role_id)))
        
        if not options:
            options.append(discord.SelectOption(label="No roles configured", value="0"))

        self.select = discord.ui.Select(placeholder="Select role to assign", min_values=1, max_values=1, options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        role_id = int(self.select.values[0])
        if role_id == 0:
            return await interaction.response.send_message("❌ No roles configured.", ephemeral=True)

        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Role not found in server.", ephemeral=True)

        await interaction.response.send_modal(RoleAssignmentModal(self.message, self.user_id, self.parent_view, role))

class RoleRequestCloseModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(label="Reason", style=discord.TextStyle.long, placeholder="Reason for closing", required=True)

    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔒 Closing ticket in 5 seconds...\n**Reason:** {self.reason.value}")

        transcript_lines = [f"Transcript for {interaction.channel.name}", f"Closed by: {interaction.user}", f"Reason: {self.reason.value}", "-"*30]
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            author = str(msg.author)
            content = msg.content
            if msg.embeds:
                content += " [Embed]"
            if msg.attachments:
                content += f" [Attachments: {', '.join([a.url for a in msg.attachments])}]"
            transcript_lines.append(f"[{timestamp}] {author}: {content}")
        
        transcript_bytes = "\n".join(transcript_lines).encode('utf-8')
        t_file = discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{interaction.channel.name}.txt")

        # Extract info for embed
        original_embed = self.message.embeds[0]
        
        opened_by_text = "Unknown"
        user_id = None
        if original_embed.footer and original_embed.footer.text:
            match = re.search(r"ID: (\d+)", original_embed.footer.text)
            if match:
                user_id = int(match.group(1))
                opened_by_text = f"<@{user_id}>"
        
        claimed_by_text = "N/A"
        for field in original_embed.fields:
            if field.name == "Assigned By":
                claimed_by_text = field.value
                break
        
        open_time_text = interaction.channel.created_at.strftime('%B %d, %Y %I:%M %p')

        embed = discord.Embed(title="Ticket Closed", color=config.EMBED_COLOR, timestamp=discord.utils.utcnow())
        embed.add_field(name="Ticket ID", value=interaction.channel.name, inline=True)
        embed.add_field(name="Opened By", value=opened_by_text, inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Open Time", value=open_time_text, inline=True)
        embed.add_field(name="Claimed By", value=claimed_by_text, inline=True)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        embed.set_footer(text="NepPath | Role Request Log", icon_url=config.AVATAR_URL)

        transcript_channel = interaction.guild.get_channel(1444275027909546024)
        if transcript_channel:
            await transcript_channel.send(embed=embed, file=t_file)

        # DM User
        if user_id:
            try:
                member = interaction.guild.get_member(user_id) or await interaction.guild.fetch_member(user_id)
                if member:
                    dm_embed = discord.Embed(
                        title="Ticket Closed",
                        description=f"Your role request ticket has been closed.",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    dm_embed.add_field(name="Reason", value=self.reason.value, inline=False)
                    dm_embed.add_field(name="Assigned By", value=interaction.user.mention, inline=True)
                    dm_embed.set_footer(text="NepPath | Role Request", icon_url=config.AVATAR_URL)
                    await member.send(embed=dm_embed)
            except Exception:
                pass

        await asyncio.sleep(5)
        await interaction.channel.delete()

class RoleRequestAssignView(discord.ui.View):
    def __init__(self, server_link: str = None):
        super().__init__(timeout=None)
        if server_link:
            server_link = server_link.strip()
            # Validate URL to prevent errors (no spaces, must have dot if protocol added)
            if server_link and " " not in server_link:
                if not server_link.startswith(("http://", "https://", "discord://")):
                    server_link = f"https://{server_link}"
                
                # Only add if it looks somewhat valid
                if "." in server_link:
                    self.add_item(discord.ui.Button(label="Discord", style=discord.ButtonStyle.link, url=server_link))

    @discord.ui.button(label="Assigned", style=discord.ButtonStyle.success, custom_id="role_req_assign_btn")
    async def assigned_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        if not any(role.id in config.AUTHORIZED_ASSIGN_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You are not authorized to assign roles.", ephemeral=True)

        # Get data from embed
        embed = interaction.message.embeds[0]
        
        # Extract User ID from footer
        user_id = None
        if embed.footer and embed.footer.text:
            match = re.search(r"ID: (\d+)", embed.footer.text)
            if match:
                user_id = int(match.group(1))
        
        if not user_id:
            return await interaction.response.send_message("❌ Could not find user ID in message.", ephemeral=True)

        await interaction.response.send_message("Select the role to assign:", view=AssignRoleSelectView(interaction.message, user_id, self), ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="role_req_close_btn", emoji="🔒")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You are not authorized to close this ticket.", ephemeral=True)
        
        await interaction.response.send_modal(RoleRequestCloseModal(interaction.message))

class RoleRequestModal(discord.ui.Modal, title="Role Request"):
    vtc_name = discord.ui.TextInput(label="Your VTC Name", placeholder="e.g. NepPath VTC", required=True)
    vtc_role = discord.ui.TextInput(label="Your VTC Role", placeholder="e.g. Driver", required=True)
    server_link = discord.ui.TextInput(label="Your Server Link", placeholder="https://discord.gg/...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        target_category_id = getattr(config, "ROLE_REQUEST_CATEGORY_ID", 1444276048710860810)
        target_category = interaction.guild.get_channel(target_category_id)
        
        if not target_category or not isinstance(target_category, discord.CategoryChannel):
            return await interaction.followup.send("❌ Configuration Error: Target category not found.", ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_id in config.STAFF_ROLE_ID:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        target_channel = await interaction.guild.create_text_channel(
            name=f"role-{interaction.user.name}",
            category=target_category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📝 Role Request",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="VTC Name", value=self.vtc_name.value, inline=True)
        embed.add_field(name="VTC Role", value=self.vtc_role.value, inline=True)
        embed.add_field(name="Requester", value=interaction.user.mention, inline=False)
        
        # Store ID in footer for retrieval
        embed.set_footer(text=f"Requester ID: {interaction.user.id}", icon_url=config.AVATAR_URL)

        view = RoleRequestAssignView(server_link=self.server_link.value)
        
        await target_channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Your role request has been submitted: {target_channel.mention}", ephemeral=True)

class RoleRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="fill your role request", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<a:Ticket:1455807330607435886>"), custom_id="role_req_fill_btn")
    async def fill_req(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(RoleRequestModal())
        except discord.NotFound:
            pass

def setup(bot: commands.Bot):
    role_group = app_commands.Group(name="role", description="Role commands")

    @role_group.command(name="req", description="Send Role Request Embed (Staff Only)")
    async def req(interaction: discord.Interaction):
        if not any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)

        embed = discord.Embed(
            title="<a:role_req:1455822154359767096>・ 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐑𝐨𝐥𝐞𝐬",
            description=(
                "<:info:1455400720173109382>  Request a Role\n"
                "**Need a specific role? Open a ticket here! <a:Ticket:1455807330607435886>**\n\n"
                "✅ Fill your role request (e.g., Driver, Media, Event Staff, etc.)\n"
                "✅ Our staff will review and assign it as soon as possible.\n"
                "✅ Please do not spam multiple tickets for the same role.\n\n"
                "🔒 Only you and staff can see your ticket."
            ),
            color=config.EMBED_COLOR
        )

        if hasattr(config, "ROLE_REQUEST_FORM_URL") and config.ROLE_REQUEST_FORM_URL:
            embed.set_image(url=config.ROLE_REQUEST_FORM_URL)
        
        target_channel = interaction.channel
        if hasattr(config, "REQUEST_ROLE_EMBED") and config.REQUEST_ROLE_EMBED:
            c = interaction.guild.get_channel(config.REQUEST_ROLE_EMBED)
            if c:
                target_channel = c

        await target_channel.send(embed=embed, view=RoleRequestView())
        await interaction.response.send_message(f"✅ Embed sent to {target_channel.mention}", ephemeral=True)

    bot.tree.add_command(role_group)