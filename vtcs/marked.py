import os
import re
import aiohttp
import traceback
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import config

# ---------- Staff check helper ----------
def is_staff_member(member: discord.Member) -> bool:
    try:
        return any(role.id in config.STAFF_ROLE_ID for role in member.roles)
    except:
        return False

# ---------- Mark Attendance Button ----------
class MarkAttendanceView(discord.ui.View):
    def __init__(self, event_link: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label='I Will Be There', style=discord.ButtonStyle.link, url=event_link))

# ---------- /mark command setup ----------
def setup(bot: commands.Bot):
    @bot.tree.command(
        name="mark",
        description="Staff only: Create a Mark Attendance embed from a TruckersMP event link."
    )
    @app_commands.describe(
        event_link="TruckersMP event URL, e.g. https://truckersmp.com/events/12345",
        channel="Channel to post the embed",
    )
    async def mark(
        interaction: discord.Interaction,
        event_link: str,
        channel: discord.TextChannel
    ):
        # ----- Check staff permission -----
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ You are not staff.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)

        # ----- Extract numeric event ID -----
        match = re.search(r"/events/(\d+)", event_link)
        if not match:
            return await interaction.followup.send("❌ Could not find an event ID in that link.", ephemeral=True)

        event_id = match.group(1)
        api_url = f"https://api.truckersmp.com/v2/events/{event_id}"

        # ----- Fetch from TruckersMP API -----
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send(f"❌ TruckersMP API returned HTTP {resp.status}.", ephemeral=True)
                    data = await resp.json()
        except Exception as e:
            traceback.print_exc()
            return await interaction.followup.send(f"❌ Failed to contact TruckersMP API: `{e}`", ephemeral=True)

        if not data.get("response"):
            return await interaction.followup.send("❌ Could not fetch event data.", ephemeral=True)

        event_info = data["response"]
        event_name = event_info.get("name", "TruckersMP Event")
        event_start = event_info.get("meetup_at")
        event_banner = event_info.get("banner")
        event_vtc = event_info.get("vtc")
        vtc_name = None
        vtc_avatar = None
        if isinstance(event_vtc, dict):
            vtc_name = event_vtc.get("name")
            vtc_avatar = event_vtc.get("logo")

        # ---------- Parse color ----------
        embed_color = discord.Color(config.EMBED_COLOR)

        # ----- Format footer timestamp -----
        footer_text = "Powered by NepPath"
        if event_start:
            try:
                evt = event_start.rstrip("Z")
                dt = datetime.fromisoformat(evt).replace(tzinfo=timezone.utc)
                utc_str = dt.strftime("%H:%M UTC")
                npt_dt = dt + timedelta(hours=5, minutes=45)
                npt_str = npt_dt.strftime("%H:%M NPT")
                footer_text = f"NepPath | {utc_str} | {npt_str}"
            except Exception:
                pass

        # ----- Build mentions and description -----
        mentions = []
        drivers_role = interaction.guild.get_role(config.DRIVER_ROLE_ID)
        if drivers_role:
            mentions.append(drivers_role.mention)

        mention_text = " ".join(mentions)
        description_body = "**🙏 𝐏𝐥𝐳 𝐊𝐢𝐧𝐝𝐥𝐲 𝐌𝐚𝐫𝐤 𝐘𝐨𝐔𝐑 𝐀𝐭𝐭𝐞𝐧𝐝𝐚𝐧𝐜𝐞 𝐎𝐧 𝐓𝐡𝐢𝐬 𝐄𝐯𝐞𝐧𝐭 : ❤️**"
        full_description = f"{mention_text}\n\n{description_body}" if mention_text else description_body

        # ----- Build embed -----
        embed = discord.Embed(
            title=event_name, url=event_link, description=full_description,
            color=embed_color
        )

        if vtc_name:
            embed.set_author(name=f"{vtc_name} Attending This Event", icon_url=config.AVATAR_URL)
        else:
            embed.set_author(name="Event Attendance", icon_url=config.AVATAR_URL)

        if event_banner:
            embed.set_image(url=event_banner)
        if vtc_avatar:
            embed.set_thumbnail(url=vtc_avatar)

        embed.set_footer(text=footer_text, icon_url=config.AVATAR_URL)

        view = MarkAttendanceView(event_link=event_link)

        await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions(roles=True))
        await interaction.followup.send(f"✅ Attendance embed sent to {channel.mention}", ephemeral=True)
