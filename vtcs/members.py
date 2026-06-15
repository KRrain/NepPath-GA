import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
from collections import defaultdict
import config
import time

CUSTOM_ROLE_ORDER = [
    "👑 | Founder",
    "🦅 | CEO",
    "🗂️ | Manager",
    "🧑‍💼 | HR Team",
    "🎪 | Event Manager",
    "🎥 | Media Team",
    "📝 | Recruitment Team",
    "🔴 | Streamer",
    "⚜️ | NepPath King Driver",
    "🚚 | Master Driver",
    "🚚 | Senior Driver",
    "🚚 | Junior Driver",
    "🚚 | Trainee Driver"
]

# Helper for permissions
def is_staff(member: discord.Member) -> bool:
    return any(role.id in config.STAFF_ROLE_ID for role in member.roles)

async def fetch_members_api(vtc_id: int):
    url = f"https://api.truckersmp.com/v2/vtc/{vtc_id}/members?t={int(time.time())}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not data["error"]:
                        return data["response"]["members"]
        except Exception:
            pass
    return None

async def fetch_members_html(vtc_id: int):
    url = f"https://truckersmp.com/vtc/{vtc_id}/members?t={int(time.time())}"
    members = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Generic scraper for TMP members table
                    table = soup.find("table")
                    if table:
                        rows = table.find_all("tr")
                        for row in rows:
                            cols = row.find_all("td")
                            if len(cols) >= 2:
                                # Name is usually in the first column
                                name_tag = cols[0].find("a")
                                if name_tag:
                                    username = name_tag.get_text(strip=True)
                                else:
                                    username = cols[0].get_text(strip=True)
                                
                                # Role is usually in the last column
                                role = cols[-1].get_text(strip=True)
                                
                                if username and role:
                                    members.append({"username": username, "role": role})
        except Exception:
            pass
    return members if members else None

async def fetch_roles_order(vtc_id: int):
    url = f"https://truckersmp.com/vtc/{vtc_id}/roles?t={int(time.time())}"
    roles = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Scrape role names from panel headings or card headers
                    # This assumes roles are listed in order on the page
                    # Using select for better coverage of Bootstrap classes
                    for header in soup.select(".card-header, .panel-heading, h3.card-title"):
                        text = header.get_text(strip=True)
                        if text and text not in roles:
                            roles.append(text)
        except Exception:
            pass
    return roles

def get_role_priority(role_name: str) -> int:
    """Helper to sort roles by rank (Highest first)"""
    role = role_name.lower()
    if "founder" in role or "owner" in role or "leader" in role: return 0
    if "ceo" in role or "chief executive" in role or "director" in role: return 1
    if "coo" in role or "chief operating" in role or "vice" in role or "admin" in role: return 2
    if "general manager" in role: return 3
    if "human resources" in role or "hr" in role: return 4
    if "manager" in role: return 5
    if "supervisor" in role: return 6
    if "event" in role: return 7
    if "media" in role: return 8
    if "driver" in role: return 9
    if "recruit" in role or "trainee" in role: return 10
    return 99

def setup_members_command(bot: commands.Bot):
    @bot.tree.command(name="members", description="List VTC Members from TruckersMP")
    async def members(interaction: discord.Interaction):
        await interaction.response.defer()
        
        vtc_id = config.VTC_ID
        
        # 1. Try HTML (Preferred for up-to-date roles)
        members_data = await fetch_members_html(vtc_id)
        source = "HTML"
        
        # 2. Fallback to API
        if not members_data:
            members_data = await fetch_members_api(vtc_id)
            source = "API"
            
        if not members_data:
            return await interaction.followup.send("❌ Could not fetch members from TruckersMP.")
            
        # Fetch live role order
        live_role_order = await fetch_roles_order(vtc_id)

        # Group by Role
        roles_map = defaultdict(list)
        for m in members_data:
            raw_role = m.get("role", "Member")
            u = m.get("username", "Unknown")
            
            roles_map[raw_role].append(u)
            
        # Build Embed
        embed = discord.Embed(
            title=f"VTC Members",
            color=discord.Color(0xff5a20),
            url=f"https://truckersmp.com/vtc/{vtc_id}/members"
        )
        embed.set_footer(text=f"NepPath | Source: {source}", icon_url=config.AVATAR_URL)
        
        # Sort roles by priority
        def role_sorter(item):
            role_name = item[0]
            
            # 1. Custom Order
            if role_name in CUSTOM_ROLE_ORDER:
                return CUSTOM_ROLE_ORDER.index(role_name)

            # Try to find in live order first (case-insensitive)
            for i, r in enumerate(live_role_order):
                if r.lower() == role_name.lower():
                    return 100 + i
            # Fallback to static priority
            return 200 + get_role_priority(role_name)

        sorted_roles = sorted(roles_map.items(), key=role_sorter)
        
        for role, users in sorted_roles:
            # Sort users alphabetically
            users.sort(key=str.lower)
            
            # Escape markdown
            users_clean = [u.replace("_", "\\_").replace("*", "\\*") for u in users]
            
            # Beautiful list format
            user_str = ""
            for i, user in enumerate(users_clean):
                entry = f"• {user}\n"
                if len(user_str) + len(entry) > 1015:
                    user_str += f"• ... (+{len(users_clean) - i} more)"
                    break
                user_str += entry
            
            role_display = f"{role}" if any(x in role.lower() for x in ["ceo", "founder", "owner"]) else f"{role}"
            role_display += f" ({len(users)})"
            embed.add_field(name=role_display, value=user_str, inline=True)
            
        await interaction.followup.send(embed=embed)