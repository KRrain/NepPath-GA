import discord
from discord import app_commands
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import config
from datetime import datetime
import random

DRIVER_ID_BANNER = "https://i.imgur.com/6Fnov98.png"
GENERATED_ID_BACKGROUND_URL = "https://i.imgur.com/n8AymYi.png"

def load_font(size, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except:
        return ImageFont.load_default()

class GrabIDModal(discord.ui.Modal, title="Grab NepPath Driver ID"):
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
    member_since = discord.ui.TextInput(
        label="Member since",
        placeholder="e.g., 15/01/2024 or 02112025 or 021125",
        required=True,
        max_length=10
    )
    avatar_image_link = discord.ui.TextInput(
        label="Avatar Image Link (Optional)",
        placeholder="e.g., https://i.imgur.com/your_image.png",
        required=False,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user

        tmp_name = self.tmp_username.value.strip()
        role_name = self.vtc_role.value.strip().upper()
        member_since_raw = self.member_since.value.strip()
        
        # Format to DD/MM/YYYY
        member_since_date = member_since_raw
        if len(member_since_raw) == 8 and member_since_raw.isdigit():
            # DDMMYYYY -> DD/MM/YYYY
            member_since_date = f"{member_since_raw[0:2]}/{member_since_raw[2:4]}/{member_since_raw[4:8]}"
        elif len(member_since_raw) == 6 and member_since_raw.isdigit():
            # DDMMYY -> DD/MM/20YY
            member_since_date = f"{member_since_raw[0:2]}/{member_since_raw[2:4]}/20{member_since_raw[4:6]}"
        
        avatar_link = self.avatar_image_link.value.strip()

        # Determine Avatar
        avatar_url = avatar_link if avatar_link else str(member.display_avatar.url)
        accent_rgb = (35, 114, 129)
        id_number = ''.join([str(random.randint(0, 9)) for _ in range(8)])

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}

        # --- Image Generation ---
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(GENERATED_ID_BACKGROUND_URL) as bg_resp:
                if bg_resp.status != 200:
                    return await interaction.followup.send("❌ Error: Could not load ID card template.", ephemeral=True)
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

        # Process Avatar (circular, 180x180)
        avatar_raw = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((180, 180))
        avatar_bg = Image.new("RGBA", avatar_raw.size, (255, 90, 32, 255))
        avatar_bg.paste(avatar_raw, (0, 0), avatar_raw)

        mask = Image.new("L", avatar_bg.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0) + avatar_bg.size, fill=255)

        avatar_position = (70, 140)
        img.paste(avatar_bg, avatar_position, mask)
        draw.ellipse([avatar_position[0]-2, avatar_position[1]-2, avatar_position[0]+avatar_bg.width+2, avatar_position[1]+avatar_bg.height+2], outline=accent_rgb, width=4)

        # Load Fonts
        f_header = load_font(42, True)
        f_title = load_font(38, True)
        f_sub = load_font(30)
        f_label = load_font(20, True)
        f_id_num = load_font(28, True)

        W, H = img.size
        text_x = (370 + W) // 2

        # Header
        draw.text((W // 2, 40), "NEPPATH DRIVER ID", fill=accent_rgb, font=f_header, anchor="mt")

        # Name
        display_name = tmp_name.upper()
        title_font = f_title if len(display_name) <= 15 else load_font(32 if len(display_name) <= 20 else 26, True)
        draw.text((text_x, 110), "NAME", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 140), display_name, fill=(60, 60, 60), font=title_font, anchor="mt")

        # VTC Role
        draw.text((text_x, 210), "VTC RANK", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 240), role_name, fill=(60, 60, 60), font=f_sub, anchor="mt")

        # Member since (date)
        draw.text((text_x, 310), "Member since", fill=accent_rgb, font=f_label, anchor="mt")
        draw.text((text_x, 340), member_since_date, fill=(60, 60, 60), font=f_sub, anchor="mt")

        # License Number (lower part) - bigger and bolder
        f_label_large = load_font(26, True)
        f_id_num_large = load_font(36, True)
        draw.text((W // 2, 410), "LICENSE NUMBER", fill=accent_rgb, font=f_label_large, anchor="mt")
        draw.text((W // 2, 445), id_number, fill=(255, 255, 255), font=f_id_num_large, anchor="mt")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        file = discord.File(buf, filename=f"driver_id_{member.id}.png")
        embed = discord.Embed(
            title="🆔 Your NepPath Driver ID",
            color=config.EMBED_COLOR,
            timestamp=datetime.now()
        )
        embed.set_image(url=f"attachment://driver_id_{member.id}.png")
        embed.set_footer(text="NepPath | Driver Identification", icon_url=config.AVATAR_URL)
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)


class DriverIDView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Grab NepPath ID", style=discord.ButtonStyle.primary, emoji="🆔", custom_id="grab_driver_id_button")
    async def grab_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GrabIDModal())


def get_driver_id_embed():
    embed = discord.Embed(
        title="🆔 NepPath Driver ID System",
        description=(
            "Welcome to the **NepPath Driver ID System**.\n\n"
            "Click the button below to grab your official NepPath Driver ID.\n\n"
            "**You will need to provide:**\n"
            "• Your TruckersMP Username\n"
            "• Your VTC Role\n"
            "• Your TruckersMP Profile ID"
        ),
        color=config.EMBED_COLOR
    )
    embed.set_image(url=DRIVER_ID_BANNER)
    embed.set_footer(text="NepPath | Driver Identification", icon_url=config.AVATAR_URL)
    return embed


def setup(bot):
    """Registers the /id command and sends embed to the designated channel."""

    @bot.tree.command(name="id", description="Send the Driver ID embed to the designated channel (Staff only)")
    async def id_command(interaction: discord.Interaction):
        # Check staff permission
        is_staff = interaction.user.guild_permissions.administrator or any(
            role.id in config.STAFF_ROLE_ID for role in interaction.user.roles
        )
        if not is_staff:
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        channel = bot.get_channel(config.DRIVER_ID_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Driver ID channel not found.", ephemeral=True)
            return

        embed = get_driver_id_embed()
        await channel.send(embed=embed, view=DriverIDView())
        await interaction.response.send_message(f"✅ Driver ID embed sent to {channel.mention}", ephemeral=True)

    # Register the command to the guild
    if hasattr(config, "GUILD_ID") and config.GUILD_ID:
        bot.tree.add_command(id_command, guild=discord.Object(id=config.GUILD_ID))
    else:
        bot.tree.add_command(id_command)


