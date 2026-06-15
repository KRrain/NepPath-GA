import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import re
from datetime import datetime
import config

TRUCKERSMP_API_URL = f"https://api.truckersmp.com/v2/vtc/{config.VTC_ID}"
TRUCKERSMP_WEB_URL = f"https://truckersmp.com/vtc/{config.VTC_ID}"

async def fetch_vtc_data():
    """
    Fetches VTC data from TruckersMP API.
    Falls back to HTML scraping if API fails.
    """
    async with aiohttp.ClientSession() as session:
        # 1. Try TruckersMP API
        try:
            async with session.get(TRUCKERSMP_API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not data["error"]:
                        return parse_api_data(data["response"])
        except Exception as e:
            print(f"[VTC] API Error: {e}")

        # 2. Fallback to HTML Scraping
        try:
            async with session.get(TRUCKERSMP_WEB_URL) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return parse_html_data(html)
        except Exception as e:
            print(f"[VTC] HTML Error: {e}")

    return None

def parse_api_data(data):
    # Socials
    socials = []
    if data.get("socials"):
        for k, v in data["socials"].items():
            if v:
                socials.append(f"[{k.capitalize()}]({v})")
    socials_str = " | ".join(socials) if socials else "None"

    # Games
    games = []
    if data.get("games"):
        if data["games"].get("ats"): games.append("ATS")
        if data["games"].get("ets"): games.append("ETS2")
    games_str = ", ".join(games) if games else "None"

    # Date
    created = data.get("created", "N/A")
    try:
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        created = dt.strftime("%d %b %Y")
    except:
        pass

    return {
        "name": data.get("name", "Unknown"),
        "slogan": data.get("slogan", ""),
        "logo": data.get("picture"),
        "members": data.get("members_count", "N/A"),
        "owner": data.get("owner_username", "N/A"),
        "recruitment": data.get("recruitment", "N/A"),
        "language": data.get("language", "N/A"),
        "tag": data.get("tag", "N/A"),
        "created": created,
        "games": games_str,
        "socials": socials_str,
        "dlcs": "See VTC Page",
        "partners": "See VTC Page",
        "source": "TruckersMP API"
    }

def parse_html_data(html):
    # Basic regex to extract info from HTML
    name_match = re.search(r'<title>(.*?) - TruckersMP</title>', html)
    logo_match = re.search(r'class="profile-picture".*?src="(.*?)"', html)
    slogan_match = re.search(r'class="slogan">(.*?)<', html)
    
    return {
        "name": name_match.group(1) if name_match else "Unknown VTC",
        "slogan": slogan_match.group(1).strip() if slogan_match else "N/A",
        "logo": logo_match.group(1) if logo_match else None,
        "members": "N/A",
        "owner": "N/A",
        "recruitment": "N/A",
        "language": "N/A",
        "tag": "N/A",
        "created": "N/A",
        "games": "N/A",
        "socials": "N/A",
        "dlcs": "N/A",
        "partners": "N/A",
        "source": "HTML Scraping (Limited)"
    }

def setup_vtc(bot: commands.Bot):
    print("🚚 Loading VTC commands...")

    @bot.tree.command(name="my_vtc", description="Display VTC Information")
    async def my_vtc(interaction: discord.Interaction):
        await interaction.response.defer()
        
        data = await fetch_vtc_data()
        
        if not data:
            return await interaction.followup.send("❌ Failed to retrieve VTC information.")

        embed = discord.Embed(
            title=data["name"],
            description=data["slogan"],
            color=config.EMBED_COLOR,
            url=TRUCKERSMP_WEB_URL,
            timestamp=datetime.utcnow()
        )
        
        if data["logo"]:
            embed.set_thumbnail(url=data["logo"])
            
        embed.add_field(name="Owner", value=data["owner"], inline=True)
        embed.add_field(name="Recruitment", value=data["recruitment"], inline=True)
        embed.add_field(name="Members", value=str(data["members"]), inline=True)
        embed.add_field(name="Tag", value=data["tag"], inline=True)
        embed.add_field(name="Language", value=data["language"], inline=True)
        embed.add_field(name="Created", value=data["created"], inline=True)
        embed.add_field(name="Supported Games", value=data["games"], inline=True)
        embed.add_field(name="DLCs Required", value=data["dlcs"], inline=True)
        embed.add_field(name="Partners", value=data["partners"], inline=True)
        embed.add_field(name="Socials", value=data["socials"], inline=False)

        embed.set_footer(text=f"{config.FOOTER_TEXT}", icon_url=config.FOOTER_ICON)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Visit VTC Page", style=discord.ButtonStyle.link, url=TRUCKERSMP_WEB_URL))

        await interaction.followup.send(embed=embed, view=view)

    print("✅ VTC commands added.")