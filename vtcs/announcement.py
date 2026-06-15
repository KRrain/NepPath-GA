import discord
from discord import app_commands
import aiohttp
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import config

# ================= HELPERS =================
def format_distance(raw: str):
    nums = re.findall(r"\d+", raw.replace(",", ""))
    if not nums:
        return raw
    return f"{int(nums[0]):,} KM"

def fmt_time(ts):
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    utc = dt.strftime("%H:%M UTC")
    npt = (dt + timedelta(hours=5, minutes=45)).strftime("%H:%M NPT")
    return utc, npt

# ================= SCRAPE DESTINATION =================
async def scrape_destination(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                html = await r.text()
    except Exception:
        return "TBA"

    soup = BeautifulSoup(html, "html.parser")
    th = soup.find("th", string=lambda s: s and "destination" in s.lower())
    if th:
        td = th.find_next_sibling("td")
        if td:
            return td.text.strip()
    return "TBA"

# ================= SCRAPE ROUTE IMAGE =================
async def scrape_route_image(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                html = await r.text()
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")
    h3 = soup.find("h3", class_="modal-title", string=lambda s: s and "event route" in s.lower())
    if not h3:
        return None

    modal_body = h3.find_parent("div", class_="modal-header")
    if modal_body:
        modal_body = modal_body.find_next_sibling("div", class_="modal-body")
        if modal_body:
            img = modal_body.find("img")
            if img and img.get("src"):
                return img["src"]

    return None

# ================= MODAL =================
class AnnounceModal(discord.ui.Modal, title="Event Announcement"):
    event_link = discord.ui.TextInput(label="Event Link", required=True)
    distance = discord.ui.TextInput(label="Distance (KM)", required=True)
    slot = discord.ui.TextInput(label="Slot Number", required=True)
    slot_image = discord.ui.TextInput(label="Slot Image URL", required=True)

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await create_announcement(
            interaction,
            self.channel,
            self.event_link.value,
            self.distance.value,
            self.slot.value,
            self.slot_image.value,
        )

# ================= CORE =================
async def create_announcement(interaction, channel, link, distance_raw, slot, slot_img):
    try:
        event_id = link.split("events/")[1].split("/")[0]
    except Exception:
        return await interaction.followup.send("❌ Invalid event link", ephemeral=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.truckersmp.com/v2/events/{event_id}") as r:
            api = await r.json()

    event = api.get("response", {})

    start_city = (
        event.get("departure", {}).get("city")
        or event.get("departure", {}).get("name")
        or "TBA"
    )

    destination = await scrape_destination(link)
    route_image = await scrape_route_image(link)

    meetup_utc, meetup_npt = fmt_time(event["meetup_at"])
    depart_utc, depart_npt = fmt_time(event["start_at"])
    date_str = datetime.fromisoformat(
        event["start_at"].replace("Z", "+00:00")
    ).strftime("%A, %B %d, %Y")

    embed1 = discord.Embed(
        title=f"📢 {event.get('name', 'Event')}",
        url=link,
        description=f"""
** **
**📅 Date: {date_str}**

**🎮 Game: {event.get('game')}**

**🖥 Server: {event.get('server', {}).get('name', 'Unknown')}**

**🕒 Meetup: {meetup_utc} | {meetup_npt}**

**🚀 Departure: {depart_utc} | {depart_npt}**

**📍 Start Location: {start_city}**

**🏁 Destination: {destination}**

**📏 Distance: {format_distance(distance_raw)}**

**#️⃣ Slot Number:** **{slot}**
** **
""",
        color=discord.Color.from_rgb(255, 90, 32)
    )

    embed1.set_footer(text="Powered by NepPath", icon_url=config.AVATAR_URL)
    embed1.set_image(url=slot_img)

    embeds = [embed1]

    if route_image:
        embed2 = discord.Embed(title="🗺 Event Route", color=discord.Color.from_rgb(255, 90, 32))
        embed2.set_image(url=route_image)
        embed2.set_footer(text="Powered by NepPath", icon_url=config.AVATAR_URL)
        embeds.append(embed2)

    ping_role = interaction.guild.get_role(config.PING_ROLE_ID)

    await channel.send(
        content=ping_role.mention if ping_role else None,
        embeds=embeds
    )

    await interaction.followup.send("✅ Announcement sent!", ephemeral=True)

# ================= SETUP =================
def setup(bot):

    @bot.tree.command(name="announcement", description="Create TruckersMP event announcement")
    async def announcement(interaction: discord.Interaction, channel: discord.TextChannel):
        if not any(r.id in config.STAFF_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ No permission", ephemeral=True)

        await interaction.response.send_modal(
            AnnounceModal(channel)
    )
