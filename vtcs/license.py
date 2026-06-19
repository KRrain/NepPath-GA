import discord
from discord import app_commands
import io
import aiohttp # Keep aiohttp for web requests
from PIL import Image, ImageDraw, ImageFont # PIL for image manipulation
import config
from datetime import datetime
import random

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
    """Load LiberationSans font bundled with the project (works on all platforms incl. Zeabur)."""
    try:
        font_path = "fonts/LiberationSans-Bold.ttf" if bold else "fonts/LiberationSans-Regular.ttf"
        return ImageFont.truetype(font_path, size)
    except Exception:
        try:
            return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
        except:
            return ImageFont.load_default()

# --- New Modal for License Details Input ---
class LicenseDetailsModal(discord.ui.Modal, title="Enter License Details"):
    tmp_username = discord.ui.TextInput(
        label="TMP Username",
        placeholder="Enter your TruckersMP username",
        required=True,
        max_length=50
    )
    vtc_role = discord.ui.TextInput(
        label="VTC Role",
        placeholder="e.g., Driver, Manager, Founder",
        required=True,
        max_length=50
    )
    vtc_joined = discord.ui.TextInput(
        label="VTC Joined (DD/MM/YYYY)",
        placeholder="e.g., 15/01/2024",
        required=True,
        max_length=10,
        min_length=10
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

        tmp_player_name = self.tmp_username.value.strip()
        vtc_rank_display = self.vtc_role.value.strip().upper()
        vtc_joined_str = self.vtc_joined.value.strip()
        avatar_image_link_value = self.avatar_image_link.value.strip()

        # Validate TMP Username
        if not tmp_player_name:
            return await interaction.followup.send("❌ TMP Username is required.", ephemeral=True)

        # Validate VTC Joined date format
        try:
            datetime.strptime(vtc_joined_str, "%d/%m/%Y")
        except ValueError:
            return await interaction.followup.send("❌ Invalid date format. Please use DD/MM/YYYY (e.g., 15/01/2024).", ephemeral=True)

        # Determine Avatar
        avatar_url = avatar_image_link_value if avatar_image_link_value else str(member.display_avatar.url)
        accent_rgb = (35, 114, 129)

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        # --- Image Generation ---
        async with aiohttp.ClientSession(headers=headers) as session:
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

        # Generate random 12-digit license number
        license_no = ''.join([str(random.randint(0, 9)) for _ in range(12)])

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
        f_header = load_font(300, True)
        f_title = load_font(50, True)
        f_sub = load_font(42)
        f_label = load_font(28, True)

        # Render Text
        W, H = img.size
        text_x = (350 + W) // 2
        draw.text((W // 2, 35), "NEPPATH DRIVER LICENSE", fill=accent_rgb, font=f_header, anchor="mt")
        
        display_name = tmp_player_name.upper()
        title_font = f_title if len(display_name) <= 15 else load_font(38 if len(display_name) <= 20 else 32, True)
        draw.text((text_x, 120), "NAME", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 155), display_name, fill=(60, 60, 60), font=title_font, anchor="mt")
        
        draw.text((text_x, 235), "VTC RANK", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 275), vtc_rank_display, fill=(60, 60, 60), font=f_sub, anchor="mt")
        draw.text((text_x, 355), "VTC JOINED", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 350), vtc_joined_str.upper(), fill=(60, 60, 60), font=f_sub, anchor="mt")
        draw.text((text_x, 420), "LICENSE NO", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 450), license_no, fill=(255, 255, 255), font=f_sub, anchor="mt")

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
