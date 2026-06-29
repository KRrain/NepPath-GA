# ---------------- book.py ----------------

import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from dotenv import load_dotenv
import traceback
import json
import re
import config

# ---------------- CONFIG ----------------
load_dotenv()
STAFF_ROLE_ID = config.STAFF_ROLE_ID
PING_ROLE_ID = config.AUTHORIZED_ASSIGN_ROLES

DEFAULT_COLOR = discord.Color(0xff5a20)
JSON_FILE = config.BOOKING_JSON_FILE

COLOR_OPTIONS = {
    "blue": discord.Color.blue(),
    "red": discord.Color.red(),
    "green": discord.Color.green(),
    "yellow": discord.Color.gold(),
    "purple": discord.Color.purple(),
    "orange": discord.Color.orange(),
    "white": discord.Color.from_rgb(255, 255, 255),
    "black": discord.Color.from_rgb(0, 0, 0),
}

# ---------- Persistent Storage ----------
try:
    with open(JSON_FILE, "r") as f:
        loaded = json.load(f)
        booking_messages = loaded if isinstance(loaded, dict) else {}
except Exception:
    booking_messages = {}

user_submissions = {}  # {message_id: {user_id: set(slots)}}

def save_json():
    try:
        os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
        with open(JSON_FILE, "w") as f:
            json.dump(booking_messages, f, indent=4)
    except Exception:
        traceback.print_exc()

# ---------- Helpers ----------
def is_staff_member(member: discord.Member) -> bool:
    try:
        return any(role.id in STAFF_ROLE_ID for role in member.roles)
    except Exception:
        return False

async def parse_slot_range(slot_range: str):
    try:
        if "-" in slot_range:
            start, end = map(int, slot_range.split("-"))
            if start < 1 or end < start:
                raise ValueError
            return [f"Slot {i}" for i in range(start, end + 1)]
        else:
            # Single number input: treat as 1 to N
            count = int(slot_range)
            if count < 1: raise ValueError
            return [f"Slot {i}" for i in range(1, count + 1)]
    except Exception:
        return None

def parse_color(color_str: str):
    if not color_str:
        return None
    try:
        if color_str.lower() in COLOR_OPTIONS:
            return COLOR_OPTIONS[color_str.lower()]
        if color_str.startswith("#"):
            color_str = color_str[1:]
        return discord.Color(int(color_str, 16))
    except Exception:
        return None

def format_slot_text(slot_name, vtc=None):
    """Returns Slot text with bold and 2 newlines"""
    if vtc:
        return f"🚛 **{slot_name}: {vtc}**\n\n"
    return f"💺 **{slot_name}: Available **\n\n"

# ---------------- Slot Booking Modal ----------------
class SlotBookingModal(discord.ui.Modal, title="Book Slot"):
    vtc_name = discord.ui.TextInput(label="VTC Name", placeholder="Enter your VTC name", max_length=100)
    slot_number = discord.ui.TextInput(label="Slot Number(s)", placeholder="e.g. 1, 6", max_length=100)

    def __init__(self, message_id: str):
        super().__init__()
        self.message_id = message_id
        data = booking_messages.get(message_id)
        slots_dict = (data or {}).get("slots", {})
        available = [s.replace("Slot ", "") for s, v in slots_dict.items() if not v]

        if available:
            preview = ", ".join(available[:10])
            if len(available) > 10:
                preview += ", ..."
            placeholder = f"Multi Book: {preview}"
            if len(placeholder) > 100:
                placeholder = placeholder[:97] + "..."
            self.slot_number.placeholder = placeholder
        else:
            self.slot_number.placeholder = "No slots available."

    async def on_submit(self, interaction: discord.Interaction):
        try:
            msg_id = self.message_id
            data = booking_messages.get(msg_id)
            if not data:
                return await interaction.response.send_message("❌ Booking data not found.", ephemeral=True)

            slots_dict = data["slots"]
            raw_input = self.slot_number.value
            requested_slots = []
            
            parts = [p.strip() for p in raw_input.split(',') if p.strip()]
            if not parts:
                return await interaction.response.send_message("❌ Please enter at least one slot number.", ephemeral=True)

            user_id = str(interaction.user.id)
            user_submissions.setdefault(msg_id, {})
            user_submissions[msg_id].setdefault(user_id, set())

            for part in parts:
                if not part.isdigit():
                    return await interaction.response.send_message(f"❌ Invalid slot number: `{part}`", ephemeral=True)
                
                s_name = f"Slot {int(part)}"
                if s_name not in slots_dict:
                    return await interaction.response.send_message(f"❌ Slot `{part}` does not exist.", ephemeral=True)
                if slots_dict[s_name]:
                    return await interaction.response.send_message(f"❌ Slot `{part}` is already booked.", ephemeral=True)
                if s_name in user_submissions[msg_id][user_id]:
                    return await interaction.response.send_message(f"❌ You already submitted slot `{part}`.", ephemeral=True)
                requested_slots.append(s_name)

            # Save user request
            for s_name in requested_slots:
                user_submissions[msg_id][user_id].add(s_name)

            slots_display = ", ".join(requested_slots)
            await interaction.response.send_message(f"✅ Request submitted for: **{slots_display}**", ephemeral=True)

            # Log to staff channel with ping
            log_channel = interaction.client.get_channel(config.STAFF_LOG_CHANNEL_ID)
            if log_channel:
                booking_channel = interaction.client.get_channel(data["channel_id"])
                mention_roles = " ".join(f"<@&{rid}>" for rid in PING_ROLE_ID)
                embed = discord.Embed(color=discord.Color.red())
                embed.set_author(name="📥 Slot Booking Request", icon_url=config.AVATAR_URL)
                embed.description = f"{mention_roles}" if mention_roles else ""
                if booking_channel:
                    embed.add_field(name="📺 Channel", value=booking_channel.mention, inline=False)
                embed.add_field(name="👤 User", value=interaction.user.mention, inline=False)             
                embed.add_field(name="🚛 VTC Name", value=self.vtc_name.value, inline=False)
                embed.add_field(name="💺 Slot Number", value=slots_display, inline=False)
                embed.add_field(name="🏠 Server", value=interaction.guild.name, inline=False)
                # Store Message ID in footer for persistence
                embed.set_footer(text=f"NepPath | Bookings | ID: {msg_id}", icon_url=config.AVATAR_URL)
                embed.timestamp = datetime.now()

                view = ApproveDenyView()
                await log_channel.send(embed=embed, view=view)

        except Exception:
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error while processing booking.", ephemeral=True)

# ---------------- Book Slot Button ----------------
class BookSlotView(discord.ui.View):
    def __init__(self, message_id=None):
        super().__init__(timeout=None)
        self.message_id = message_id
        # Disable if full
        if message_id:
            data = booking_messages.get(message_id)
            if data and not any(v is None for v in data["slots"].values()):
                for child in self.children:
                    if isinstance(child, discord.ui.Button) and child.custom_id == "book_slot_button":
                        child.disabled = True

    @discord.ui.button(label="📌 Book Slot", style=discord.ButtonStyle.green, custom_id="book_slot_button")
    async def book_slot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = booking_messages.get(str(interaction.message.id))
        if not data:
            return await interaction.response.send_message("❌ Invalid booking message.", ephemeral=True)
        if not any(v is None for v in data["slots"].values()):
            try:
                await interaction.response.send_message("❌ No available slots.", ephemeral=True)
            except discord.errors.HTTPException:
                await interaction.followup.send("❌ No available slots.", ephemeral=True)
            button.disabled = True
            await interaction.message.edit(view=BookSlotView(message_id=str(interaction.message.id)))
            return
        try:
            await interaction.response.send_modal(SlotBookingModal(str(interaction.message.id)))
        except discord.errors.HTTPException:
            await interaction.followup.send("❌ Could not open booking modal. Please try again.", ephemeral=True)

# ---------------- Approve/Deny/Remove Approval ----------------
class ApproveDenyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _get_booking_data(self, interaction: discord.Interaction):
        """Reconstruct state from the embed"""
        embed = interaction.message.embeds[0]
        
        # Extract Message ID from footer
        if not embed.footer or not embed.footer.text:
            return None
        footer_text = embed.footer.text
        msg_id_match = re.search(r"ID: (\d+)", footer_text)
        if not msg_id_match:
            return None
        message_id = msg_id_match.group(1)
        
        # Extract User ID
        user_field = discord.utils.get(embed.fields, name="👤 User")
        if not user_field: return None
        user_match = re.search(r"<@!?(\d+)>", user_field.value)
        user_id = user_match.group(1) if user_match else None
        
        # Extract VTC Name
        vtc_field = discord.utils.get(embed.fields, name="🚛 VTC Name")
        vtc_name = vtc_field.value if vtc_field else "Unknown"
        
        # Extract Slots
        slot_field = discord.utils.get(embed.fields, name="💺 Slot Number")
        slot_numbers = [s.strip() for s in slot_field.value.split(",")] if slot_field else []
        
        return {
            "message_id": message_id,
            "user_id": user_id,
            "vtc_name": vtc_name,
            "slot_numbers": slot_numbers
        }

    async def _notify_user(self, bot, user_id, vtc_name, slot_numbers, approved: bool, staff_member=None):
        try:
            user = await bot.fetch_user(int(user_id))
            status = "Approved" if approved else "Denied"
            title_emoji = "✅" if approved else "❌"
            embed = discord.Embed(
                color=discord.Color.green() if approved else discord.Color.red(),
                description=f"👤 **User:** <@{user_id}>\n🚛 **VTC Name:** {vtc_name}\n🔢 **Slot:** {', '.join(slot_numbers)}\n🛡️ **Action by:** {staff_member.mention if staff_member else 'Staff'}"
            )
            embed.set_author(name=f"{title_emoji} Slot {status}", icon_url=config.AVATAR_URL)
            embed.set_footer(text="NepPath | Bookings", icon_url=config.AVATAR_URL)
            embed.timestamp = datetime.now()
            await user.send(embed=embed)
        except Exception:
            pass

    async def _update_main_embed(self, bot, message_id):
        data = booking_messages.get(message_id)
        if not data:
            return
        channel = bot.get_channel(data["channel_id"])
        if not channel:
            return
        try:
            msg = await channel.fetch_message(int(message_id))
            embed = discord.Embed(
                description="".join(format_slot_text(s, v) for s, v in data["slots"].items()),
                color=discord.Color(data["color"])
            )
            embed.set_author(name=data["title"], icon_url=config.AVATAR_URL)
            embed.set_footer(text="NepPath | Bookings", icon_url=config.AVATAR_URL)
            embed.timestamp = datetime.now()
            if data.get("image"):
                embed.set_image(url=data["image"])
            view = BookSlotView(message_id=message_id)
            # Disable book button if full
            if not any(v is None for v in data["slots"].values()):
                for child in view.children:
                    if isinstance(child, discord.ui.Button) and child.custom_id == "book_slot_button":
                        child.disabled = True
            await msg.edit(embed=embed, view=view)
        except Exception:
            traceback.print_exc()

    async def _update_log_embed(self, interaction: discord.Interaction, message_id, approved: bool, new_view: discord.ui.View):
        embed = interaction.message.embeds[0]
        user_val, vtc_val, slot_val, channel_val = "", "", "", ""
        for field in embed.fields:
            if field.name == "📺 Channel":
                channel_val = field.value
            elif field.name == "👤 User":
                user_val = field.value
            elif field.name == "🚛 VTC Name":
                vtc_val = field.value
            elif field.name == "💺 Slot Number":
                slot_val = field.value

        status_field_name = "✅ Approved By" if approved else "❌ Denied By"
        status_color = discord.Color.green() if approved else discord.Color.red()

        embed.clear_fields()
        embed.description = "" # Clear role pings
        if channel_val:
            embed.add_field(name="📺 Channel", value=channel_val, inline=False)
        embed.add_field(name="👤 User", value=user_val, inline=False)
        embed.add_field(name="🚛 VTC Name", value=vtc_val, inline=False)
        embed.add_field(name="💺 Slot Number", value=slot_val, inline=False)
        embed.add_field(name=status_field_name, value=interaction.user.mention, inline=False)
        embed.color = status_color
        embed.set_footer(text=f"NepPath | Bookings | ID: {message_id}", icon_url=config.AVATAR_URL)
        embed.timestamp = datetime.now()
        await interaction.message.edit(embed=embed, view=new_view)

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green, custom_id="approve_booking_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ You are not staff.", ephemeral=True)

        data_state = await self._get_booking_data(interaction)
        if not data_state:
            return await interaction.response.send_message("❌ Could not recover booking data from this message.", ephemeral=True)

        message_id = data_state["message_id"]
        user_id = data_state["user_id"]
        vtc_name = data_state["vtc_name"]
        slot_numbers = data_state["slot_numbers"]

        data = booking_messages.get(message_id)
        if not data:
            return await interaction.response.send_message("❌ Booking data not found.", ephemeral=True)
        
        for s in slot_numbers:
            if data["slots"].get(s):
                return await interaction.response.send_message(f"❌ {s} already approved.", ephemeral=True)
            data["slots"][s] = vtc_name
            user_submissions.get(message_id, {}).get(user_id, set()).discard(s)
            
        save_json()

        await self._update_main_embed(interaction.client, message_id)
        await self._notify_user(interaction.client, user_id, vtc_name, slot_numbers, True, interaction.user)

        # Update buttons state
        new_view = ApproveDenyView()
        for child in new_view.children:
            if child.custom_id == "approve_booking_btn" or child.custom_id == "deny_booking_btn":
                child.disabled = True
            if child.custom_id == "remove_approval_btn":
                child.disabled = False

        await self._update_log_embed(interaction, message_id, True, new_view)
        await interaction.response.send_message("✅ Approved.", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red, custom_id="deny_booking_btn")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ You are not staff.", ephemeral=True)

        data_state = await self._get_booking_data(interaction)
        if not data_state:
            return await interaction.response.send_message("❌ Could not recover booking data.", ephemeral=True)

        message_id = data_state["message_id"]
        user_id = data_state["user_id"]
        vtc_name = data_state["vtc_name"]
        slot_numbers = data_state["slot_numbers"]

        for s in slot_numbers:
            user_submissions.get(message_id, {}).get(user_id, set()).discard(s)
        save_json()

        await self._notify_user(interaction.client, user_id, vtc_name, slot_numbers, False, interaction.user)

        new_view = ApproveDenyView()
        for child in new_view.children:
            if child.custom_id == "approve_booking_btn" or child.custom_id == "deny_booking_btn":
                child.disabled = True

        await self._update_log_embed(interaction, message_id, False, new_view)
        await interaction.response.send_message("❌ Denied.", ephemeral=True)

    @discord.ui.button(label="♻ Remove Approval", style=discord.ButtonStyle.gray, custom_id="remove_approval_btn")
    async def remove_approval(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ You are not staff.", ephemeral=True)

        data_state = await self._get_booking_data(interaction)
        if not data_state:
            return await interaction.response.send_message("❌ Could not recover booking data.", ephemeral=True)

        message_id = data_state["message_id"]
        slot_numbers = data_state["slot_numbers"]

        data = booking_messages.get(message_id)
        if not data:
            return await interaction.response.send_message("❌ Slot not approved.", ephemeral=True)

        for s in slot_numbers:
            data["slots"][s] = None
        save_json()

        await self._update_main_embed(interaction.client, message_id)
        await interaction.response.send_message(f"♻ Removed approval for {', '.join(slot_numbers)}.", ephemeral=True)

# ---------------- /book Command ----------------
def setup_book_command(bot: commands.Bot):

    @bot.tree.command(name="book", description="Staff only: Create booking embed")
    @app_commands.describe(channel="Channel to post booking embed")
    async def book(interaction: discord.Interaction, channel: discord.TextChannel):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ You are not staff.", ephemeral=True)

        class CreateBookingModal(discord.ui.Modal, title="Create Booking Embed"):
            title_input = discord.ui.TextInput(label="Embed Title", max_length=100)
            slot_range_input = discord.ui.TextInput(label="Slot Range", placeholder="Example: 1-10 or 20", max_length=10)
            color_input = discord.ui.TextInput(label="Color Name or Hex", placeholder="red / #FF0000", max_length=20)
            image_input = discord.ui.TextInput(label="Image URL (optional)", required=False)

            async def on_submit(self, modal_interaction: discord.Interaction):
                slots_list = await parse_slot_range(self.slot_range_input.value)
                if not slots_list:
                    return await modal_interaction.response.send_message("❌ Invalid slot range.", ephemeral=True)

                hex_color = parse_color(self.color_input.value) or DEFAULT_COLOR

                desc = "".join(format_slot_text(s) for s in slots_list)
                embed = discord.Embed(description=desc, color=hex_color)
                embed.set_author(name=self.title_input.value, icon_url=config.AVATAR_URL)
                embed.set_footer(text="NepPath | Bookings", icon_url=config.AVATAR_URL)
                embed.timestamp = datetime.now()
                if self.image_input.value:
                    embed.set_image(url=self.image_input.value)

                sent_msg = await channel.send(embed=embed, view=BookSlotView())
                booking_messages[str(sent_msg.id)] = {
                    "channel_id": channel.id,
                    "title": self.title_input.value,
                    "color": hex_color.value,
                    "image": self.image_input.value or "",
                    "slots": {slot: None for slot in slots_list}
                }
                save_json()

                await modal_interaction.response.send_message(
                    f"✅ Booking embed created with {len(slots_list)} slots.", ephemeral=True
                )

        await interaction.response.send_modal(CreateBookingModal())
