import discord
from discord import app_commands
import json
from pathlib import Path
from datetime import datetime, timedelta
import re
import aiohttp
import random
import io
import config
from vtcs.announcement import scrape_route_image

# ================== PING CONFIG - EASILY ADD/EDIT ROLES HERE ==================
TICKET_PING_CONFIG = {
    "Invite Us": ["event_manager", "staff"],
    "Partnership DM": ["event_manager", "staff"],
    "Support Team": ["event_manager", "staff"],
    "CEO Request": ["ceo"],
    "Founder Request": ["founder"],
    "Event Enquiry": ["event_manager", "staff"],
    "Event Team": ["event_manager", "staff"],
    "Media Team": ["event_manager", "staff"],
}

# Role mapping for easy extension
ROLE_MAPPING = {
    "staff": config.STAFF_ROLE_ID[0], # Using first staff ID for mapping if single ID needed, or handle list logic
    "event_manager": config.EVENT_MANAGER_ROLE_ID,
    "ceo": config.CEO_ROLE_ID,
    "founder": config.FOUNDER_ROLE_ID,
    # Add more like: "media": MEDIA_ROLE_ID, etc.
}

def is_staff(member: discord.Member):
    if not isinstance(member, discord.Member):
        return False
    return any(role.id in config.STAFF_ROLE_ID for role in member.roles)

def _load_ticket_records():
    config.TICKET_RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not config.TICKET_RECORD_FILE.exists():
        return []
    try:
        with config.TICKET_RECORD_FILE.open("r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def _save_ticket_records(records):
    config.TICKET_RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    with config.TICKET_RECORD_FILE.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


def _create_ticket_record(channel: discord.TextChannel, opener: discord.User, reason: str | None = None, team: str | None = None):
    records = _load_ticket_records()
    next_id = 1
    if records:
        try:
            next_id = max(r.get("ticket_id", 0) for r in records) + 1
        except Exception:
            next_id = len(records) + 1

    record = {
        "ticket_id": next_id,
        "channel_id": channel.id,
        "channel_name": channel.name,
        "opened_by_id": opener.id,
        "opened_by": str(opener),
        "team": team,
        "reason": reason,
        "open_time": datetime.utcnow().isoformat()
    }
    records.append(record)
    _save_ticket_records(records)
    return record


def _get_ticket_record_by_channel(channel_id: int):
    records = _load_ticket_records()
    for r in records:
        if r.get("channel_id") == channel_id:
            return r
    return None


def _update_ticket_record(channel_id: int, **fields):
    """Update an existing ticket record by channel_id or create a minimal one if missing."""
    records = _load_ticket_records()
    for r in records:
        if r.get("channel_id") == channel_id:
            r.update(fields)
            _save_ticket_records(records)
            return r

    # not found -> create a minimal record
    next_id = 1
    if records:
        try:
            next_id = max(rr.get("ticket_id", 0) for rr in records) + 1
        except Exception:
            next_id = len(records) + 1

    record = {
        "ticket_id": next_id,
        "channel_id": channel_id,
        "channel_name": None,
        "opened_by_id": None,
        "opened_by": None,
        "team": None,
        "reason": None,
        "open_time": datetime.utcnow().isoformat(),
    }
    record.update(fields)
    records.append(record)
    _save_ticket_records(records)
    return record


async def _safe_send_modal(interaction: discord.Interaction, modal: discord.ui.Modal):
    """Safely send a modal, falling back to a followup message if the interaction is already acknowledged or expired."""
    try:
        if not interaction.response.is_done():
            await interaction.response.send_modal(modal)
        else:
            await interaction.followup.send(
                "Unable to open modal: interaction already acknowledged or expired. Please run the command again.",
                ephemeral=True,
            )
    except discord.NotFound:
        try:
            await interaction.followup.send(
                "Unable to open modal: interaction expired. Please run the command again.",
                ephemeral=True,
            )
        except Exception:
            pass
    except Exception:
        try:
            await interaction.followup.send("Unable to open modal. Please run the command again.", ephemeral=True)
        except Exception:
            pass

def get_ping_roles(guild: discord.Guild, ticket_type: str):
    """Returns list of discord.Role objects to ping for a given ticket type"""
    role_keys = TICKET_PING_CONFIG.get(ticket_type, ["event_manager", "staff"])
    roles = []
    for key in role_keys:
        role_id = ROLE_MAPPING.get(key)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                roles.append(role)
    return roles

async def fetch_truckersmp_event(event_id: int):
    url = f"https://api.truckersmp.com/v2/events/{event_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data.get("response")

# -------------------- MODALS --------------------
class AcceptModal(discord.ui.Modal, title="Accept Ticket"):
    slot_number = discord.ui.TextInput(label="Slot Number", placeholder="Enter slot number", required=True)

    def __init__(self, channel: discord.TextChannel, requester: discord.User):
        super().__init__()
        self.channel = channel
        self.requester = requester

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        description = (
            "<a:tick:1396694919766085683> 𝐘𝐨𝐮𝐫 𝐢𝐧𝐯𝐢𝐭𝐚𝐭𝐢𝐨𝐧 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐚𝐜𝐜𝐞𝐩𝐭𝐞𝐝.\n\n"
            "🎉 We sincerely thank you for inviting NepPath to participate in your event. We are pleased to confirm our attendance and look forward to being part of this valuable opportunity.\n\n"
            f"{self.requester.mention}, we will meet you on the event day. 🚛🌟🎉"
        )

        embed = discord.Embed(
            title="✅ Ticket Accepted!",
            description=description,
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name="💺 Slot Number", value=f"**{self.slot_number.value}**", inline=True)
        embed.add_field(name="🛡️ Action by", value=interaction.user.mention, inline=True)
        embed.add_field(name="📌 Event Markdown", value=f"[𝐂𝐋𝐈𝐂𝐊 𝐇𝐄𝐑𝐄]({config.MAEK_DOWN_CHANNEL})", inline=True)
        embed.set_footer(text="NepPath | Staff Team", icon_url=config.AVATAR_URL)
        await self.channel.send(
               embed=embed,
               allowed_mentions=discord.AllowedMentions(users=True)
        )

        try:
            await self.requester.send(embed=embed)
        except discord.Forbidden:
            pass

        # Update ticket record
        _update_ticket_record(
            self.channel.id,
            claimed_by_id=interaction.user.id,
            claimed_by=str(interaction.user),
            claimed_time=datetime.utcnow().isoformat()
        )

        config.DATA_FILE.parent.mkdir(exist_ok=True)
        data = []
        if config.DATA_FILE.exists():
            try:
                with open(config.DATA_FILE, "r") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data = content
            except Exception:
                pass
        data.append({"user_id": self.requester.id, "slot": self.slot_number.value, "time": datetime.utcnow().isoformat()})
        with open(config.DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        await interaction.followup.send("✅ Ticket accepted and slot saved!", ephemeral=True)

        # Post to Attendees Channel if it's an event invite
        if hasattr(config, "MARK_ATTENDEES_CHANNEL_ID") and config.MARK_ATTENDEES_CHANNEL_ID:
            attendees_channel = interaction.guild.get_channel(config.MARK_ATTENDEES_CHANNEL_ID)
            if attendees_channel:
                # Try to find event ID from channel history (looking for bot's invite embed)
                event_id = None
                async for msg in self.channel.history(limit=20, oldest_first=True):
                    if msg.author.id == interaction.client.user.id and msg.embeds:
                        embed = msg.embeds[0]
                        if embed.url:
                            match = re.search(r"events/(\d+)", embed.url)
                            if match:
                                event_id = int(match.group(1))
                                break
                        desc = embed.description or ""
                        match = re.search(r"truckersmp\.com/events/(\d+)", desc)
                        if match:
                            event_id = int(match.group(1))
                            break
                
                if event_id:
                    event = await fetch_truckersmp_event(event_id)
                    if event:
                        meetup_at_str = event.get('meetup_at', '')
                        time_str = ""
                        if meetup_at_str:
                            try:
                                meetup_dt = datetime.fromisoformat(meetup_at_str.rstrip('Z'))
                                npt_offset = timedelta(hours=5, minutes=45)
                                meetup_npt = meetup_dt + npt_offset
                                time_str = f" | {meetup_dt.strftime('%H:%M')} UTC | {meetup_npt.strftime('%H:%M')} NPT"
                            except ValueError:
                                pass

                        evt_embed = discord.Embed(
                            title=event.get('name', 'Event'),
                            url=f"https://truckersmp.com/events/{event_id}",
                            description="📇 𝐃𝐞𝐚𝐫 𝑵𝒆𝒑𝑷𝒂𝒕𝒉 𝐌𝐞𝐦𝐛𝐞𝐫𝐬 🙏;\n\n🙏 𝐏𝐥𝐳 𝐊𝐢𝐧𝐝𝐥𝐲 𝐌𝐚𝐫𝐤 𝐘𝐨𝐮𝐫 𝐀𝐭𝐭𝐞𝐧𝐝𝐚𝐧𝐜𝐞 𝐎𝐧 𝐓𝐡𝐢𝐬 𝐄𝐯𝐞𝐧𝐭 : ❤️",
                            color=config.EMBED_COLOR
                        )
                        icon_url = interaction.guild.icon.url if interaction.guild.icon else config.AVATAR_URL
                        evt_embed.set_author(name="NEPPATH ATTENDEES EVENT", icon_url=icon_url)
                        if event.get('banner'):
                            evt_embed.set_image(url=event.get('banner'))
                        evt_embed.set_footer(text=f"NepPath{time_str}", icon_url=config.AVATAR_URL)

                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label="🗣️ 𝐈 𝐖𝐢𝐥𝐥 𝐁𝐞 𝐓𝐡𝐞𝐫𝐞 👁️", url=f"https://truckersmp.com/events/{event_id}"))
                        
                        content = ""
                        if hasattr(config, "DRIVER_ROLE_ID") and config.DRIVER_ROLE_ID:
                            content = f"<@&{config.DRIVER_ROLE_ID}>"

                        try:
                            await attendees_channel.send(content=content, embed=evt_embed, view=view)
                        except Exception as e:
                            print(f"Failed to send attendees message: {e}")

class DeclineModal(discord.ui.Modal, title="Decline Ticket"):
    reason = discord.ui.TextInput(label="Reason", style=discord.TextStyle.long, placeholder="Enter reason")

    def __init__(self, channel: discord.TextChannel, requester: discord.User):
        super().__init__()
        self.channel = channel
        self.requester = requester

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="❌ Ticket Declined",
            description=(
                "<a:X_anim:1455783086020104255> **We sincerely regret to inform you.**\n\n"
                "⚠️ Unfortunately, your invitation has been declined.\n"
                f"{self.requester.mention}, thank you for considering NepPath. 🙏"
            ),
            color=0xFF0000,
            timestamp=datetime.utcnow()
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name="Reason", value=f"**{self.reason.value}**", inline=True)
        embed.add_field(name="Action by", value=interaction.user.mention, inline=True)
        embed.set_footer(text="NepPath | Staff Team", icon_url=config.AVATAR_URL)
        await self.channel.send(embed=embed)

        try:
            await self.requester.send(embed=embed)
        except discord.Forbidden:
            pass

        # Update ticket record
        _update_ticket_record(
            self.channel.id,
            claimed_by_id=interaction.user.id,
            claimed_by=str(interaction.user),
            claimed_time=datetime.utcnow().isoformat()
        )

        config.DATA_FILE.parent.mkdir(exist_ok=True)
        data = []
        if config.DATA_FILE.exists():
            try:
                with open(config.DATA_FILE, "r") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data = content
            except Exception:
                pass
        data.append({"user_id": self.requester.id, "reason": self.reason.value, "time": datetime.utcnow().isoformat()})
        with open(config.DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        await interaction.followup.send("❌ Ticket declined and reason saved!", ephemeral=True)

class CloseTicketModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(label="Reason", style=discord.TextStyle.long, placeholder="Reason for closing", required=True)

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Ensure ticket is claimed by closer if not already claimed
        record = _get_ticket_record_by_channel(self.channel.id)
        if not record or not record.get("claimed_by_id"):
            record = _update_ticket_record(
                self.channel.id,
                claimed_by_id=interaction.user.id,
                claimed_by=str(interaction.user),
                claimed_time=datetime.utcnow().isoformat()
            )

        transcript_channel = interaction.guild.get_channel(config.TRANSCRIPT_CHANNEL_ID)
        # Build a summary embed similar to the provided design and attach the transcript file
        ticket_id = record.get("ticket_id") if record else self.channel.name
        opener = None
        claimed_by = None
        reason_text = None
        transcript_lines = [f"Transcript for {self.channel.name}", f"Closed by: {interaction.user}", f"Reason: {self.reason.value}", "-"*30]

        async for msg in self.channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            author = str(msg.author)
            content = msg.content
            if msg.embeds:
                content += " [Embed]"
            if msg.attachments:
                content += f" [Attachments: {', '.join([a.url for a in msg.attachments])}]"
            transcript_lines.append(f"[{timestamp}] {author}: {content}")

            if not opener and not msg.author.bot:
                opener = msg
                if msg.embeds and getattr(msg.embeds[0], 'description', None):
                    reason_text = msg.embeds[0].description
                elif msg.content:
                    reason_text = msg.content
            if not claimed_by and is_staff(msg.author):
                claimed_by = msg.author
        
        transcript_bytes = "\n".join(transcript_lines).encode('utf-8')

        opened_by_text = "Unknown"
        if opener:
            opened_by_text = opener.author.mention
        elif record and record.get("opened_by_id"):
            opened_by_text = f"<@{record.get('opened_by_id')}>"
        # prefer recorded claimer if present
        claimed_by_text = "N/A"
        if record and record.get("claimed_by_id"):
            try:
                member = interaction.guild.get_member(record.get("claimed_by_id"))
                claimed_by_text = member.mention if member else f"<@{record.get('claimed_by_id')}>"
            except Exception:
                claimed_by_text = f"<@{record.get('claimed_by_id')}>"
        elif claimed_by:
            claimed_by_text = claimed_by.mention
        
        # persist claimed info if found and not already recorded
        try:
            if claimed_by:
                existing_claimed = record and record.get("claimed_by_id")
                if not existing_claimed:
                    _update_ticket_record(
                        self.channel.id,
                        claimed_by_id=claimed_by.id,
                        claimed_by=str(claimed_by),
                        claimed_time=datetime.utcnow().isoformat(),
                    )
        except Exception:
            pass

        open_time_text = self.channel.created_at.strftime('%B %d, %Y %I:%M %p') if self.channel.created_at else "N/A"

        embed = discord.Embed(title="𝐓𝐢𝐜𝐤𝐞𝐭 𝐂𝐥𝐨𝐬𝐞𝐝", color=config.EMBED_COLOR, timestamp=datetime.utcnow())
        embed.add_field(name="Ticket ID", value=str(ticket_id), inline=True)
        embed.add_field(name="Opened By", value=opened_by_text, inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Open Time", value=open_time_text, inline=True)
        embed.add_field(name="Claimed By", value=claimed_by_text, inline=True)
        
        final_reason = record.get("reason") if record and record.get("reason") else (reason_text or "N/A")
        # embed.add_field(name="Reason", value=final_reason, inline=False)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        embed.set_footer(text=datetime.utcnow().strftime('%m/%d/%Y %I:%M %p'))

        if transcript_channel:
            t_file = discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{self.channel.name}.txt")
            await transcript_channel.send(embed=embed, file=t_file)

        # DM the user
        target_user = None
        user_id = record.get("opened_by_id") if record else None

        # Fallback: Check bot embed for mention if user_id missing
        if not user_id:
            async for msg in self.channel.history(limit=10, oldest_first=True):
                if msg.author.id == interaction.client.user.id and msg.embeds:
                    desc = msg.embeds[0].description
                    if desc:
                        match = re.search(r"<@!?(\d+)>", desc)
                        if match:
                            user_id = int(match.group(1))
                            break

        if not user_id and opener:
            user_id = opener.author.id

        if user_id:
            target_user = interaction.guild.get_member(user_id)
            if not target_user:
                try:
                    target_user = await interaction.guild.fetch_member(user_id)
                except discord.NotFound:
                    try:
                        target_user = await interaction.client.fetch_user(user_id)
                    except Exception:
                        pass
                except Exception:
                    pass

        if target_user:
            try:
                await target_user.send(embed=embed)
            except Exception:
                pass

        await interaction.followup.send("✅ Ticket closed and transcript saved!", ephemeral=True)
        await self.channel.delete()

# -------------------- VIEWS --------------------
class CloseOnlyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _safe_send_modal(interaction, CloseTicketModal(interaction.channel))

class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can use these buttons.", ephemeral=True)
            return False
        return True

    async def _get_context(self, interaction: discord.Interaction):
        channel = interaction.channel
        record = _get_ticket_record_by_channel(channel.id)
        requester = None
        if record and record.get("opened_by_id"):
            requester = interaction.guild.get_member(record.get("opened_by_id"))
            if not requester:
                try:
                    requester = await interaction.guild.fetch_member(record.get("opened_by_id"))
                except:
                    pass
        
        # Fallback: Check the first bot message for a mention in the embed description
        if not requester:
            async for msg in channel.history(limit=5, oldest_first=True):
                if msg.author.id == interaction.client.user.id and msg.embeds:
                    desc = msg.embeds[0].description
                    if desc:
                        match = re.search(r"<@!?(\d+)>", desc)
                        if match:
                            user_id = int(match.group(1))
                            try:
                                requester = interaction.guild.get_member(user_id) or await interaction.guild.fetch_member(user_id)
                                if requester:
                                    break
                            except:
                                pass

        # Fallback: Try to find the first human message (likely the opener)
        if not requester:
            async for msg in channel.history(limit=20, oldest_first=True):
                if not msg.author.bot:
                    requester = msg.author
                    break

        # Fallback if record missing/member left
        if not requester:
             requester = interaction.user # Fallback to staff member to prevent crash, or handle gracefully
        
        return channel, requester

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_action_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, requester = await self._get_context(interaction)
        await _safe_send_modal(interaction, AcceptModal(channel, requester))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌", custom_id="ticket_action_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, requester = await self._get_context(interaction)
        await _safe_send_modal(interaction, DeclineModal(channel, requester))

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_action_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _safe_send_modal(interaction, CloseTicketModal(interaction.channel))

# -------------------- TICKET MODALS --------------------
class SubjectReasonModal(discord.ui.Modal):
    subject = discord.ui.TextInput(label="Subject", placeholder="Enter subject", max_length=100)
    reason = discord.ui.TextInput(label="Details", style=discord.TextStyle.long, placeholder="Explain your request", required=True)

    def __init__(self, team: str):
        super().__init__(title=f"{team} Ticket")
        self.team = team

    async def on_submit(self, interaction: discord.Interaction):
        titles = {
            "Support Team": ["🛠️ Support Request", "🔧 Help Needed", "⚡ Assistance Required"],
            "CEO Request": ["👔 CEO Invitation", "📌 CEO Attention", "✨ CEO Request"],
            "Founder Request": ["👑 Founder Invitation", "📌 Founder Attention", "✨ Founder Request"],
            "Event Enquiry": ["🎉 Event Enquiry", "📅 Event Info Request", "🚛 Event Details Needed"],
            "Event Team": ["📅 Event Team Ticket", "🎊 Event Coordination", "📝 Event Support"],
            "Media Team": ["📸 Media Request", "🎬 Media Coverage", "🎥 Media Assistance"]
        }
        embed_title = random.choice(titles.get(self.team, ["📌 Ticket Request"]))

        category = interaction.guild.get_channel(config.MANAGEMENT_TICKET_CATEGORY_ID)
        ping_roles = get_ping_roles(interaction.guild, self.team)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        for role_id in config.STAFF_ROLE_ID:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        for role in ping_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await interaction.guild.create_text_channel(
            name=f"{self.team.lower().replace(' ', '-')}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        # Persist ticket record and get numeric ticket id
        try:
            _create_ticket_record(channel, interaction.user, reason=self.reason.value, team=self.team)
        except Exception:
            pass

        # Get roles to ping
        ping_mentions = [role.mention for role in ping_roles]
        ping_text = " ".join([interaction.user.mention] + ping_mentions)

        embed = discord.Embed(
            title=embed_title,
            description=f"**{ping_text}**\n\n**Subject:** {self.subject.value}\n\n{self.reason.value}",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"NepPath | {self.team}", icon_url=config.AVATAR_URL)

        await channel.send(embed=embed, view=CloseOnlyView(), allowed_mentions=discord.AllowedMentions.all())

        await interaction.response.send_message(f"✅ Ticket opened: {channel.mention}", ephemeral=True)

class PartnershipModal(discord.ui.Modal, title="Partnership Request"):
    vtc_name = discord.ui.TextInput(label="Your VTC Name")
    vtc_link = discord.ui.TextInput(label="Your VTC Link")
    discord_link = discord.ui.TextInput(label="Discord Server Link")
    members = discord.ui.TextInput(label="VTC Member Count")
    offer = discord.ui.TextInput(label="What can your VTC offer?", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        category = interaction.guild.get_channel(config.MANAGEMENT_TICKET_CATEGORY_ID)
        ping_roles = get_ping_roles(interaction.guild, "Partnership DM")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        for role_id in config.STAFF_ROLE_ID:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        for role in ping_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await interaction.guild.create_text_channel(
            name=f"partner-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        try:
            _create_ticket_record(channel, interaction.user, reason=f"Partnership: {self.vtc_name.value}", team="Partnership")
        except Exception:
            pass
        ping_mentions = [role.mention for role in ping_roles]
        ping_text = " ".join([interaction.user.mention] + ping_mentions)

        embed = discord.Embed(
            title="🤝 Partnership Request",
            description=(
                f"**{ping_text}**\n\n"
                f"📛 **VTC Name:** {self.vtc_name.value}\n"
                f"⛓️‍💥 **VTC Link:** {self.vtc_link.value}\n"
                f"🌐 **Discord Server Link:** {self.discord_link.value}\n"
                f"👥 **Member Count:** {self.members.value}\n"
                f"🚛 **Offer:** {self.offer.value}"
            ),
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="NepPath | Management Team", icon_url=config.AVATAR_URL)

        await channel.send(embed=embed, view=CloseOnlyView(), allowed_mentions=discord.AllowedMentions.all())

        await interaction.response.send_message(f"✅ Partnership ticket created: {channel.mention}", ephemeral=True)

# -------------------- INVITE US MODAL --------------------
class InviteUsModal(discord.ui.Modal, title="Invite Us to Your Event"):
    event_link = discord.ui.TextInput(label="TruckersMP Event Link", placeholder="https://truckersmp.com/events/xxxx", required=True)
    book_slot_link = discord.ui.TextInput(label="Book Slot Link", placeholder="Slot Link (optional)", required=False, style=discord.TextStyle.short)
    manual_distance = discord.ui.TextInput(label="Distance ( e.g. 1,230 )", placeholder="Enter distance manually (optional)", required=False, style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        distance_input = self.manual_distance.value.strip() if self.manual_distance.value else ""
        if distance_input:
            # Auto-append KM if input is just numbers (e.g. "1111" -> "1111 km")
            if re.match(r"^\d+(?:,\d+)*(?:\.\d+)?$", distance_input):
                distance_input += " km"

            cleaned = distance_input.replace(' ', '').replace(',', '')
            if not re.match(r"^\d+(\.\d+)?(?:km|KM|Km|kM)?$", cleaned):
                return await interaction.followup.send(
                    "❌ Invalid distance format. Examples: `1230 km`, `1,230 km`, `1500`, `2000 KM`",
                    ephemeral=True
                )

        match = re.search(r"events/(\d+)", self.event_link.value)
        if not match:
            return await interaction.followup.send("❌ Invalid TruckersMP event link.", ephemeral=True)

        event_id = int(match.group(1))
        event = await fetch_truckersmp_event(event_id)
        if not event:
            return await interaction.followup.send("❌ Event not found on TruckersMP.", ephemeral=True)

        # Auto-fetch route image
        route_image_url = await scrape_route_image(self.event_link.value)

        category = interaction.guild.get_channel(config.CATEGORY_TICKET_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True),
        }
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID[0]) # Assuming first is main staff
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            name=f"invite-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        try:
            _create_ticket_record(channel, interaction.user, reason=f"Event Invite: {event.get('name', '')}", team="Invite")
        except Exception:
            pass

        meetup_at = datetime.fromisoformat(event.get('meetup_at', '').rstrip('Z'))
        start_at = datetime.fromisoformat(event.get('start_at', '').rstrip('Z'))
        npt_offset = timedelta(hours=5, minutes=45)

        meetup_utc_str = meetup_at.strftime('%H:%M')
        meetup_npt = meetup_at + npt_offset
        meetup_npt_str = meetup_npt.strftime('%H:%M')
        depart_utc_str = start_at.strftime('%H:%M')
        depart_npt = start_at + npt_offset
        depart_npt_str = depart_npt.strftime('%H:%M')
        date_str = start_at.strftime('%A %d %B %Y')

        game_name = "Euro Truck Simulator 2" if event.get('game') == "ETS2" else "American Truck Simulator" if event.get('game') == "ATS" else event.get('game', 'N/A')
        server_name = event.get("server", {}).get("name", "TBD")
        start_city = event.get('departure', {}).get('city', 'N/A')
        start_loc = event.get('departure', {}).get('location', 'N/A')
        start_full = f"{start_city} [{start_loc}]" if start_loc != 'N/A' else start_city
        end_city = event.get('arrive', {}).get('city', 'N/A')
        end_loc = event.get('arrive', {}).get('location', 'N/A')
        end_full = f"{end_city} [{end_loc}]" if end_loc != 'N/A' else end_city
        dlcs = event.get('dlcs', {})
        dlc_str = "NONE" if not dlcs else ', '.join(dlcs.values())

        distance_text = distance_input if distance_input else "N/A"

        details_description = (
            f"**<:controller:1397225498823884810>  Game : {game_name}**\n\n"
            f"**<:server:1397229894186045612>  Server : {server_name}**\n\n"
            f"**<:calendar1:1398462389623586847>  Date : {date_str}**\n\n"
            f"**<:meetup:1397234801034919996>  Meetup : {meetup_utc_str} (UTC) / {meetup_npt_str} (NPT)**\n\n"
            f"**<:departure:1397235350178631771>  Departure : {depart_utc_str} (UTC) / {depart_npt_str} (NPT)**\n\n"
            f"**<:gps:1397242816643727572>  Start : {start_full}**\n\n"
            f"**<:map:1397231162119688384>  End : {end_full}**\n\n"
            f"**<:DLC:1402699251909267547>  DLC Required : {dlc_str}**\n\n"
            f"**<:km:1397238154909585518>  Distance : {distance_text}**\n\n"
            f"**<:tmp:1397245714349953217>  Event Page: [Click Here]({self.event_link.value})**"
        )

        ping_roles = get_ping_roles(interaction.guild, "Invite Us")
        ping_mentions = [role.mention for role in ping_roles]
        ping_text = " ".join([interaction.user.mention] + ping_mentions)

        embed = discord.Embed(
            title=event.get('name', 'Convoy Information'),
            url=self.event_link.value,
            description=f"**{ping_text}**\n\n{details_description}",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )

        if route_image_url:
            embed.set_image(url=route_image_url)

        embed.set_footer(text="NepPath | Event Team", icon_url=config.AVATAR_URL)

        view = TicketActionView()
        if self.book_slot_link.value:
            url_val = self.book_slot_link.value.strip()
            # Validate URL to prevent HTTP 400 Bad Request
            if not url_val.startswith(("http://", "https://", "discord://")):
                if "." in url_val and " " not in url_val:
                    url_val = f"https://{url_val}"
                else:
                    url_val = None
            
            if url_val:
                view.add_item(discord.ui.Button(label="Slot Book 📙", style=discord.ButtonStyle.link, url=url_val, emoji="📙"))

        await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.all())

        review_embed = discord.Embed(
            title="📝 Event Invitation Under Review",
            description=(
                f"{interaction.user.mention}\n\n"
                "✨ Our staff team is reviewing your ticket with full attention and detail.\n\n"
                "📌 **Review Note:** Thank you for submitting your invite. Your ticket is important to us and we are carefully checking all details.\n\n"
                "You will receive updates once the review is completed. 🚛🌟🎉 Thank you for your patience and trust in NepPath!"
            ),
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        if interaction.guild.icon:
            review_embed.set_thumbnail(url=interaction.guild.icon.url)
        review_embed.set_footer(text="NepPath | Staff Team", icon_url=config.AVATAR_URL)
        await channel.send(embed=review_embed)

        await interaction.followup.send(f"✅ Event invite ticket created: {channel.mention}", ephemeral=True)

# -------------------- DROPDOWN --------------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Invite Us", emoji="📨"),
            discord.SelectOption(label="Partnership DM", emoji="🤝"),
            discord.SelectOption(label="Support Team", emoji="🛠️"),
            discord.SelectOption(label="Excuse CEO", emoji="👔"),
            discord.SelectOption(label="Excuse Founder", emoji="👑"),
            discord.SelectOption(label="Event Enquiry", emoji="🎉"),
            discord.SelectOption(label="Event Team", emoji="📅"),
            discord.SelectOption(label="Media Team", emoji="📸"),
        ]
        super().__init__(placeholder="Select ticket type...", options=options, custom_id="ticket_create_select")

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        team_map = {
            "Invite Us": "Invite Us",
            "Partnership DM": "Partnership DM",
            "Support Team": "Support Team",
            "Excuse CEO": "CEO Request",
            "Excuse Founder": "Founder Request",
            "Event Enquiry": "Event Enquiry",
            "Event Team": "Event Team",
            "Media Team": "Media Team"
        }
        team_name = team_map.get(choice)

        # Reset the dropdown selection visually
        try:
            await interaction.message.edit(view=TicketDropdownView())
        except Exception:
            pass

        if team_name == "Invite Us":
            await _safe_send_modal(interaction, InviteUsModal())
        elif team_name == "Partnership DM":
            await _safe_send_modal(interaction, PartnershipModal())
        else:
            await _safe_send_modal(interaction, SubjectReasonModal(team_name))

class TicketDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

class TicketCreateModal(discord.ui.Modal, title="Create Ticket"):
    ticket_title = discord.ui.TextInput(label="Ticket Title", max_length=100)
    ticket_message = discord.ui.TextInput(label="Message", style=discord.TextStyle.long)
    ticket_extra = discord.ui.TextInput(label="Additional Description", style=discord.TextStyle.long, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        desc = f"{self.ticket_message.value}\n\n{self.ticket_extra.value}" if self.ticket_extra.value else self.ticket_message.value
        embed = discord.Embed(
            title=self.ticket_title.value,
            description=desc,
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="NepPath | Ticket", icon_url=config.AVATAR_URL)
        await interaction.response.send_message(embed=embed, view=TicketDropdownView())

@app_commands.command(name="ticket", description="Create ticket (Staff only)")
async def ticket(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
    await _safe_send_modal(interaction, TicketCreateModal())

def setup(bot):
    bot.tree.add_command(ticket)

def register_views(bot):
    bot.add_view(TicketDropdownView())
    bot.add_view(CloseOnlyView())
    bot.add_view(TicketActionView())
