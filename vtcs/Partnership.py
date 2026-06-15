import discord
from discord import app_commands
from discord.ext import commands
import config
import aiohttp
import re
from datetime import datetime

async def fetch_vtc_info(vtc_id: int):
    url = f"https://api.truckersmp.com/v2/vtc/{vtc_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("response")
            return None

class PartnershipFillModal(discord.ui.Modal, title="Partnership Information"):
    vtc_input = discord.ui.TextInput(
        label="VTC Link or ID",
        placeholder="e.g. https://truckersmp.com/vtc/12345 or 12345",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        input_val = self.vtc_input.value.strip()
        match = re.search(r"vtc/(\d+)", input_val)
        if match:
            vtc_id = int(match.group(1))
        elif input_val.isdigit():
            vtc_id = int(input_val)
        else:
            return await interaction.followup.send("❌ Invalid VTC Link or ID provided.", ephemeral=True)

        vtc_data = await fetch_vtc_info(vtc_id)
        if not vtc_data:
            return await interaction.followup.send("❌ Could not retrieve VTC details from TruckersMP. Please check the ID/Link.", ephemeral=True)

        name = vtc_data.get("name", "Unknown")
        slogan = vtc_data.get("slogan") or "No Slogan"
        information = vtc_data.get("information") or "No Information"
        if len(information) > 1500:
            information = information[:1497] + "..."

        owner = vtc_data.get("owner_username", "Unknown")
        recruitment = vtc_data.get("recruitment", "Unknown")
        members = vtc_data.get("members_count", 0)
        tag = vtc_data.get("tag", "N/A")
        
        created_raw = vtc_data.get("created", "")
        created_display = created_raw
        try:
            dt = datetime.strptime(created_raw, "%Y-%m-%d %H:%M:%S")
            created_display = dt.strftime("%d %b %Y")
        except:
            pass

        socials = vtc_data.get("socials") or {}
        discord_link = socials.get("discord") or "N/A"
        vtc_link = f"https://truckersmp.com/vtc/{vtc_id}"
        
        vtc_link_fmt = f"[<a:right_hober1_1:1455424583493484676> 𝐕𝐓𝐂 𝐏𝐀𝐆𝐄]({vtc_link})"
        discord_link_fmt = f"[<a:right_hober1_1:1455424583493484676> 𝐃𝐈𝐒𝐂𝐎𝐑𝐃]({discord_link})" if discord_link != "N/A" else "N/A"

        description = (
            f"<:NepPath:1395694322061410334> We are pleased to announce that NepPath has officially entered into a new partnership with **{name}**.\n\n"
            f"<:right_hover:1455407281004089356> **{slogan}**\n\n"
            f"<:info:1455400720173109382> 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧\n"
            f"{information}\n\n"
            f"<:tmp:1397245714349953217> **TruckersMP VTC Link:** {vtc_link_fmt}\n\n"
            f"<:discord:1397240771031204011> **Discord Link:** {discord_link_fmt}"
        )
        
        embed = discord.Embed(
            title=f"🤝 Partnership {name}",
            description=description,
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="VTC Name", value=name, inline=True)
        embed.add_field(name="Tag", value=tag, inline=True)
        embed.add_field(name="Members", value=str(members), inline=True)
        embed.add_field(name="Created", value=created_display, inline=True)
        embed.add_field(name="Owner", value=owner, inline=True)
        embed.add_field(name="Recruitment", value=recruitment, inline=True)

        if vtc_data.get("logo"):
            embed.set_thumbnail(url=vtc_data.get("logo"))
        if vtc_data.get("cover"):
            embed.set_image(url=vtc_data.get("cover"))
        
        embed.set_footer(text="NepPath | Partnership", icon_url=config.AVATAR_URL)
        
        result_channel_id = getattr(config, "PARTNERSHIP_RESULT_CHANNEL_ID", 1455409070260621355)
        result_channel = interaction.guild.get_channel(result_channel_id)
        
        if result_channel:
            await result_channel.send(embed=embed)
            await interaction.followup.send(f"✅ Partnership announcement posted!\n**Check: {result_channel.mention}!**", ephemeral=True)
        else:
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("✅ Partnership announcement posted!", ephemeral=True)

class PartnershipView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fill VTC", style=discord.ButtonStyle.primary, custom_id="partnership_fill_vtc_btn", emoji="📝")
    async def fill_vtc(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_roles = getattr(config, "FILL_VTC_AUTHORIZED_ROLES", [])
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You do not have permission to use this button.", ephemeral=True)

        await interaction.response.send_modal(PartnershipFillModal())

@app_commands.command(name="partnership", description="Send partnership information request embed")
async def partnership(interaction: discord.Interaction):
    is_staff = False
    for role in interaction.user.roles:
        if role.id in config.STAFF_ROLE_ID:
            is_staff = True
            break
            
    if not is_staff:
        return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    channel_id = getattr(config, "PARTNERSHIP_CHANNEL_ID", 1455383683786866759)
    channel = interaction.guild.get_channel(channel_id)
    
    if not channel:
        return await interaction.followup.send(f"❌ Channel with ID {channel_id} not found.", ephemeral=True)

    embed = discord.Embed(
        title="🤝 Partnership Information Request",
        description="Dear Valued Partner,\n\nWe kindly request you to click the “Fill VTC” button to complete your information.\nOur system (Bot) will automatically retrieve your details from TruckersMP; you only need to provide your VTC link or ID.\n\nThank you very much for your cooperation and continued support. We sincerely appreciate it.\n\nWith respect,\nNepPath Administration",
        color=config.EMBED_COLOR,
        timestamp=datetime.utcnow()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="NepPath | Administration", icon_url=config.AVATAR_URL)

    await channel.send(embed=embed, view=PartnershipView())
    await interaction.followup.send(f"✅ Partnership embed sent to {channel.mention}", ephemeral=True)

def setup(bot: commands.Bot):
    bot.tree.add_command(partnership)