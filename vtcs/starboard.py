import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime

import config


STAR_EMOJI = "⭐"


CONGRATS_MESSAGES = [
    "Amazing message!",
    "Community loved this!",
    "Star-worthy content 🌟",
    "This deserves recognition!",
    "Pure gold ✨",
]


# ================= PERMISSION CHECK =================
def is_staff(interaction: discord.Interaction) -> bool:
    if not interaction.user.roles:
        return False
    return any(role.id in config.STAFF_ROLE_ID for role in interaction.user.roles)


# ================= VIEW =================
class StarboardWatchedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Channels to Watch...",
        min_values=0,
        max_values=25
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg = config.load_starboard_config()
        selected_ids = [c.id for c in select.values]
        cfg["watched_channel_ids"] = selected_ids
        config.save_starboard_config(cfg)
        
        if selected_ids:
            mentions = ", ".join(f"<#{cid}>" for cid in selected_ids)
            await interaction.response.edit_message(content=f"✅ Starboard will now ONLY listen to: {mentions}", view=None)
        else:
            await interaction.response.edit_message(content="✅ Starboard will now listen to ALL channels.", view=None)

# ================= EDIT VIEWS & MODALS =================
class StarboardLimitModal(discord.ui.Modal, title="Set Star Limit"):
    limit = discord.ui.TextInput(label="Minimum Stars", placeholder="e.g. 3", min_length=1, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.limit.value)
            if val < 1: raise ValueError
            
            cfg = config.load_starboard_config()
            cfg["required_stars"] = val
            config.save_starboard_config(cfg)
            
            await interaction.response.send_message(f"✅ Star requirement updated to **{val}** ⭐", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number.", ephemeral=True)

class StarboardEditView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Set Star Limit", style=discord.ButtonStyle.primary, emoji="⭐")
    async def edit_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StarboardLimitModal())

    @discord.ui.button(label="Set Watched Channels", style=discord.ButtonStyle.secondary, emoji="📺")
    async def edit_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👇 Select the channels to watch for stars:", view=StarboardWatchedView(), ephemeral=True)

class StarboardConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        await interaction.response.send_message("Select a setting to edit:", view=StarboardEditView(), ephemeral=True)

# ================= SETUP =================
def setup(bot: commands.Bot):

    print("⭐ Loading Starboard commands...")
    starboard_group = app_commands.Group(name="starboard", description="Starboard commands")

    # ---------------- STARBOARD CONFIG ----------------
    @starboard_group.command(name="config", description="View current settings")
    async def config_cmd(interaction: discord.Interaction):

        if not is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Staff only command.", ephemeral=True
            )

        cfg = config.load_starboard_config()
        # Fixed Starboard Channel
        c_ids = [config.STARBOARD_LOG_CHANNEL_ID]
            
        limit = cfg.get("required_stars", 3)
        watched_ids = cfg.get("watched_channel_ids", [])

        embed = discord.Embed(
            title="⭐ Starboard Configuration",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=config.AVATAR_URL)

        channels_text = ", ".join(f"<#{cid}>" for cid in c_ids) if c_ids else "Not Set"
        watched_text = ", ".join(f"<#{cid}>" for cid in watched_ids) if watched_ids else "All Channels"

        embed.add_field(
            name="Starboard Channels",
            value=channels_text,
            inline=False
        )
        embed.add_field(
            name="Watched Channels",
            value=watched_text,
            inline=False
        )
        embed.add_field(
            name="Required Stars",
            value=f"{limit} ⭐",
            inline=False
        )

        embed.set_footer(
            text=config.FOOTER_TEXT,
            icon_url=config.FOOTER_ICON
        )

        await interaction.response.send_message(embed=embed, view=StarboardConfigView(), ephemeral=True)

    # ---------------- SET WATCHED CHANNELS ----------------
    @starboard_group.command(name="set_watched", description="Set channels to listen for stars (Empty = All)")
    async def set_watched(interaction: discord.Interaction):
        if not is_staff(interaction):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        
        await interaction.response.send_message("👇 Select the channels to watch for stars:", view=StarboardWatchedView(), ephemeral=True)

    # ---------------- SET LIMIT ----------------
    @starboard_group.command(name="set_limit", description="Set minimum stars required")
    async def set_limit(interaction: discord.Interaction, limit: int):
        if not is_staff(interaction):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        
        if limit < 1:
            return await interaction.response.send_message("❌ Limit must be at least 1.", ephemeral=True)

        cfg = config.load_starboard_config()
        cfg["required_stars"] = limit
        config.save_starboard_config(cfg)
        
        await interaction.response.send_message(f"✅ Star requirement updated to **{limit}** ⭐", ephemeral=True)

    # ---------------- STARBOARD LEADERBOARD ----------------
    @starboard_group.command(name="leaderboard", description="View top starred messages")
    async def leaderboard_cmd(interaction: discord.Interaction):

        lb = config.load_leaderboard()
        if "guilds" not in lb:
            lb["guilds"] = {}
        guild_id = str(interaction.guild.id)

        data = lb["guilds"].get(guild_id, {})

        # Convert data to list for sorting
        # Data structure: {msg_id: {"stars": int, "board_id": int, "channel_id": int}}
        items = []
        for msg_id, val in data.items():
            if isinstance(val, dict):
                items.append((msg_id, val.get("stars", 0), val.get("channel_id")))
            elif isinstance(val, int): # Legacy support
                items.append((msg_id, val, None))

        embed = discord.Embed(
            title="🏆 Starboard Leaderboard",
            color=config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=config.AVATAR_URL)

        if not items:
            embed.description = "No starred messages yet."
        else:
            sorted_msgs = sorted(items, key=lambda x: x[1], reverse=True)[:10]
            desc = ""
            for i, (msg_id, stars, cid) in enumerate(sorted_msgs, start=1):
                link = ""
                if cid:
                    link = f" • Jump"
                desc += f"**#{i}** • `{stars}` ⭐{link}\n"
            embed.description = desc

        embed.set_footer(
            text=config.FOOTER_TEXT,
            icon_url=config.FOOTER_ICON
        )

        await interaction.response.send_message(embed=embed)

    bot.tree.add_command(starboard_group)
    print("✅ Starboard group added to command tree.")

    # ---------------- CORE LOGIC ----------------
    async def update_starboard(payload, remove=False):
        if str(payload.emoji) != STAR_EMOJI:
            return

        if payload.guild_id is None:
            return

        # Load Config
        cfg = config.load_starboard_config()
        # Fixed Starboard Channel
        sb_channel_ids = [config.STARBOARD_LOG_CHANNEL_ID]
            
        limit = cfg.get("required_stars", 3)

        # Check watched channels
        watched_ids = cfg.get("watched_channel_ids", [])
        if watched_ids and payload.channel_id not in watched_ids:
            return

        # Ignore reactions inside ANY starboard channel
        if payload.channel_id in sb_channel_ids:
            return

        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        # Count stars
        reaction = discord.utils.get(message.reactions, emoji=STAR_EMOJI)
        star_count = reaction.count if reaction else 0

        # ---------- SAVE LEADERBOARD ----------
        lb = config.load_leaderboard()
        gid = str(guild.id)
        mid = str(message.id)

        if "guilds" not in lb:
            lb["guilds"] = {}
        lb["guilds"].setdefault(gid, {})
        
        # Get existing entry or create new
        entry = lb["guilds"][gid].get(mid)
        
        # Initialize or Migrate entry
        if entry is None or isinstance(entry, int):
            entry = {"stars": 0, "board_messages": {}, "channel_id": channel.id}
        elif "board_messages" not in entry:
            # Migration from single board_id to dict
            entry["board_messages"] = {}
            if entry.get("board_id"):
                # Assign old ID to first channel if available (best effort)
                if sb_channel_ids:
                    entry["board_messages"][str(sb_channel_ids[0])] = entry["board_id"]
            entry.pop("board_id", None)
        
        entry["stars"] = star_count
        entry["channel_id"] = channel.id # Ensure channel ID is saved

        # ---------- SEND TO STARBOARD ----------
        # Prepare Embed Content
        if star_count >= limit: 
            # Prepare Embed
            desc = message.content
            if not desc:
                desc = random.choice(CONGRATS_MESSAGES)

            embed = discord.Embed(
                description=desc,
                color=config.EMBED_COLOR,
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            
            embed.set_footer(text=f"{star_count} ⭐ | {channel.name}")
            content_str = f"🎉    **{star_count}**    ⭐   |   {channel.mention} | {message.author.mention}"

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to Message", style=discord.ButtonStyle.link, url=message.jump_url))

        # Iterate over all configured starboard channels
        for sb_id in sb_channel_ids:
            starboard_channel = guild.get_channel(sb_id)
            if not starboard_channel:
                continue
            
            sb_id_str = str(sb_id)
            existing_msg_id = entry["board_messages"].get(sb_id_str)

            if star_count >= limit:
                # Add or Edit
                if existing_msg_id:
                # Edit existing
                    try:
                        sb_msg = await starboard_channel.fetch_message(existing_msg_id)
                        await sb_msg.edit(content=content_str, embed=embed, view=view)
                    except discord.NotFound:
                        sent = await starboard_channel.send(content_str, embed=embed, view=view)
                        entry["board_messages"][sb_id_str] = sent.id
                else:
                    # Send new
                    sent = await starboard_channel.send(content_str, embed=embed, view=view)
                    entry["board_messages"][sb_id_str] = sent.id
            else:
                # Count dropped below limit -> Delete
                if existing_msg_id:
                    try:
                        sb_msg = await starboard_channel.fetch_message(existing_msg_id)
                        await sb_msg.delete()
                    except:
                        pass
                    entry["board_messages"][sb_id_str] = None

        # Save final state
        lb["guilds"][gid][mid] = entry
        config.save_leaderboard(lb)

    # ---------------- EVENTS ----------------
    @bot.event
    async def on_raw_reaction_add(payload):
        await update_starboard(payload, remove=False)

    @bot.event
    async def on_raw_reaction_remove(payload):
        await update_starboard(payload, remove=True)
