import discord
from discord import app_commands
import io
import aiohttp # Keep aiohttp for web requests
from PIL import Image, ImageDraw, ImageFont # PIL for image manipulation
import config
from datetime import datetime
import random
import re
import html

def setup(bot):
    """Registers the license command to the bot's tree."""
    bot.tree.add_command(license_command)

# Professional random banners for the license intro
LICENSE_BANNERS = [
    "https://i.imgur.com/6Fnov98.png"
]

# Official background for the generated license
GENERATED_LICENSE_BACKGROUND_URL = "https://i.imgur.com/n8AymYi.png"

def load_font(size, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except:
        return ImageFont.load_default()

# --- New Modal for License Details Input ---
class LicenseDetailsModal(discord.ui.Modal, title="Enter License Details"):
    tmp_profile_link = discord.ui.TextInput(
        label="TruckersMP Profile Link",
        placeholder="https://truckersmp.com/user/12345",
        required=True,
        max_length=100
    )
    avatar_image_link = discord.ui.TextInput(
        label="Custom Avatar Image Link (Optional)",
        placeholder="e.g., https://i.imgur.com/your_image.png",
        required=False,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user

        # Extract TMP ID from link
        match = re.search(r"user/(\d+)", self.tmp_profile_link.value)
        if not match:
            return await interaction.followup.send("❌ Invalid TruckersMP Link. Please provide a link like `https://truckersmp.com/user/12345`.", ephemeral=True)
        
        tmp_id = match.group(1)
        vtc_rank_display = "DRIVER"
        license_display_id = tmp_id
        avatar_image_link_value = self.avatar_image_link.value.strip()

        tmp_player_name = None
        tmp_join_date_str = "UNKNOWN"
        tmp_join_num = ""

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Tier 1: Attempt to fetch via Official API
                async with session.get(f"https://api.truckersmp.com/v2/player/{tmp_id}") as resp:
                    if resp.status == 200: 
                        data = await resp.json()
                        if not data.get("error"):
                            user_data = data["response"]
                            tmp_player_name = user_data.get("name")
                            # Prioritize VTC Join Date (memberSince) over Account Join Date
                            vtc_info = user_data.get("vtc", {})
                            vtc_rank_display = vtc_info.get("role", vtc_rank_display)
                            join_raw = vtc_info.get("memberSince") or user_data.get("joinDate")
                            
                            if join_raw:
                                dt_obj = datetime.strptime(join_raw, "%Y-%m-%d %H:%M:%S")
                                tmp_join_date_str = dt_obj.strftime("%d/%m/%Y")
                                tmp_join_num = dt_obj.strftime("%d%m%Y")

                # Tier 2: Fallback to HTML Scraping if API fails or name is missing
                if not tmp_player_name or tmp_join_date_str == "UNKNOWN":
                    async with session.get(f"https://truckersmp.com/user/{tmp_id}") as html_resp:
                        if html_resp.status == 200:
                            html_content = await html_resp.text()
                            
                            # Member since (for License No)
                            ms_match = re.search(r'Member since:</strong>\s*([^<]+)', html_content)
                            if ms_match:
                                try:
                                    ms_raw = " ".join(ms_match.group(1).strip().split()[:3])
                                    ms_dt = datetime.strptime(ms_raw, "%d %b %Y")
                                    tmp_join_num = ms_dt.strftime("%d%m%Y")
                                except: pass

                            # Scrape username from Player Info table
                            name_match = None
                            if not tmp_player_name:
                                name_match = re.search(r'Username</th>\s*<td[^>]*>(.*?)</td>', html_content, re.IGNORECASE)
                                if not name_match:
                                    name_match = re.search(r'<title>\s*(.*?)\'s Profile\s*[—–-]\s*TruckersMP</title>', html_content)
                                if not name_match:
                                    name_match = re.search(r'<h1>\s*<i[^>]*></i>\s*(.*?)\s*</h1>', html_content, re.DOTALL)
                                if not name_match:
                                    name_match = re.search(r'<title>(.*?) - TruckersMP</title>', html_content)
                                
                                if name_match:
                                    tmp_player_name = html.unescape(name_match.group(1).strip())

                            # Scrape TruckersMP ID from clipboard data for LICENSE NO display
                            id_scrape = re.search(r'TruckersMP ID:</strong>\s*(?:&nbsp;)?\s*<span[^>]*data-clipboard-text="(\d+)"', html_content)
                            if id_scrape:
                                license_display_id = id_scrape.group(1)

                            # Scrape VTC Role badge specifically
                            role_match = re.search(r'id="vtc_role_badge"[^>]*>(.*?)</span>', html_content)
                            if role_match:
                                vtc_rank_display = html.unescape(role_match.group(1).strip())

                            # Try to scrape VTC Join Date specifically first
                            vtc_match = re.search(r'VTC:</strong>\s*<a[^>]+>[^<]+</a>\s*\(since\s*([^)]+)\)', html_content)
                            joined_match = re.search(r'Joined:\s*([^<]+)', html_content)
                            date_match = vtc_match or joined_match or ms_match
                            
                            if date_match:
                                try:
                                    raw_date = " ".join(date_match.group(1).strip().split()[:3])
                                    dt_obj = datetime.strptime(raw_date, "%d %b %Y")
                                    tmp_join_date_str = dt_obj.strftime("%d/%m/%Y")
                                except:
                                    pass
            except Exception as e:
                print(f"⚠️ Error during TMP data extraction: {e}")

            # Clean rank from emojis/prefixes like "👑 | Founder"
            if "|" in vtc_rank_display:
                vtc_rank_display = vtc_rank_display.split("|")[-1].strip()

            # Validate that we actually found a TMP name
            if not tmp_player_name:
                return await interaction.followup.send("❌ Could not retrieve your TruckersMP username. This is often caused by temporary blocks on the TruckersMP website. Please check your link or try again in a few minutes.", ephemeral=True)

            # Determine Avatar
            avatar_url = avatar_image_link_value if avatar_image_link_value else str(member.display_avatar.url)
            accent_rgb = (35, 114, 129)

            # --- Image Generation ---
            async with session.get(GENERATED_LICENSE_BACKGROUND_URL) as bg_resp:
                if bg_resp.status != 200:
                    return await interaction.followup.send("❌ Error: Could not load license template.", ephemeral=True)
                bg_bytes = await bg_resp.read()
            
            avatar_bytes = None
            try:
                async with session.get(avatar_url) as av_resp:
                    if av_resp.status == 200:
                        avatar_bytes = await av_resp.read()
            except:
                pass
            
            if not avatar_bytes:
                async with session.get(str(member.display_avatar.url)) as av_resp:
                    if av_resp.status == 200:
                        avatar_bytes = await av_resp.read()

        if not avatar_bytes:
            return await interaction.followup.send("❌ Error: Could not load avatar image.", ephemeral=True)

        # Create Canvas
        img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Process Avatar
        avatar_raw = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((220, 220))
        # Create a background with the requested color (255, 90, 32) to fill transparency
        avatar = Image.new("RGBA", avatar_raw.size, (255, 90, 32, 255))
        avatar.paste(avatar_raw, (0, 0), avatar_raw)
        
        mask = Image.new("L", avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0) + avatar.size, fill=255)
        
        avatar_position = (70, 140)
        img.paste(avatar, avatar_position, mask)
        draw.ellipse([avatar_position[0]-2, avatar_position[1]-2, avatar_position[0]+avatar.width+2, avatar_position[1]+avatar.height+2], outline=accent_rgb, width=4)

        # Load Fonts
        f_header = load_font(48, True)
        f_title = load_font(45, True)
        f_sub = load_font(35)
        f_label = load_font(22, True)

        # Render Text
        W, H = img.size
        text_x = (350 + W) // 2
        draw.text((W // 2, 40), "NEPPATH DRIVER LICENSE", fill=accent_rgb, font=f_header, anchor="mt")
        
        display_name = tmp_player_name.upper()
        title_font = f_title if len(display_name) <= 15 else load_font(35 if len(display_name) <= 20 else 30, True)
        draw.text((text_x, 120), "NAME", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 150), display_name, fill=(60, 60, 60), font=title_font, anchor="mt")
        
        draw.text((text_x, 220), "VTC RANK", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 250), vtc_rank_display.upper(), fill=(60, 60, 60), font=f_sub, anchor="mt")
        draw.text((text_x, 320), "VTC JOINED", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 350), tmp_join_date_str.upper(), fill=(60, 60, 60), font=f_sub, anchor="mt")
        draw.text((text_x, 420), "LICENSE NO", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 450), f"{license_display_id}{tmp_join_num}", fill=(255, 255, 255), font=f_sub, anchor="mt")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        file = discord.File(buf, filename=f"license_{member.id}.png")
        embed = discord.Embed(color=config.EMBED_COLOR)
        embed.set_image(url=f"attachment://license_{member.id}.png")
        embed.set_footer(text="NepPath | Virtual Trucking Excellence", icon_url=config.AVATAR_URL)
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

class LicenseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Generate Your License", style=discord.ButtonStyle.success, emoji="💳", custom_id="generate_license_button")
    async def generate_license(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LicenseDetailsModal())

@app_commands.command(name="license", description="Open the professional driver license generation panel.")
async def license_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💳 NepPath Driver Licensing Portal",
        description=(
            "Welcome to the official NepPath VTC Licensing system. "
            "Click the button below to generate your personalized Driver License card.\n\n"
            "**Includes:**\n"
            "• Your TruckersMP Name\n"
            "• Your NepPath VTC Rank\n"
            "• Your TruckersMP Join Date\n"
            "• Your Unique License Number"
        ),
        color=config.EMBED_COLOR
    )
    embed.set_image(url=random.choice(LICENSE_BANNERS))
    embed.set_footer(text="NepPath | Road to Excellence", icon_url=config.AVATAR_URL)
    await interaction.response.send_message(embed=embed, view=LicenseView())