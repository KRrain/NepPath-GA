import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime
import config

TMP_SERVERS_API = "https://api.truckersmp.com/v2/servers"
TRAFFIC_CHANNEL_ID = config.TRAFFIC_CHANNEL_ID
GRADIENT_COLOR = 0xFF5A20


def setup(bot: commands.Bot):
    """Registers the traffic command and starts the auto-post loop."""
    traffic_cog = TrafficCog(bot)
    bot.add_cog(traffic_cog)
    bot.tree.add_command(traffic_command)
    print("✅ Traffic cog loaded.")


async def fetch_servers() -> list:
    """Fetch all TMP servers and return the response list."""
    async with aiohttp.ClientSession() as session:
        async with session.get(TMP_SERVERS_API) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("response", [])
    return []


# ---- Gradient chart helpers ----

GRADIENT_BARS = {
    0:  "🟩",   # 0-25%   green
    1:  "🟩",
    2:  "🟨",   # 25-50%  yellow
    3:  "🟨",
    4:  "🟧",   # 50-75%  orange
    5:  "🟧",
    6:  "🟥",   # 75-100% red
    7:  "🟥",
    8:  "🟥",
    9:  "🟥",
    10: "🟥",
}


def gradient_chart(players: int, maxp: int, width: int = 10) -> str:
    """Create a gradient chart row: 🟩🟩🟨🟨🟧🟧🟥🟥🟥🟥 (fills left to right)."""
    if maxp == 0:
        return "⬜" * width + " 0%"
    ratio = players / maxp
    filled = round(ratio * width)
    filled = min(filled, width)

    row = ""
    for i in range(width):
        if i < filled:
            # Pick gradient color based on position
            pct_pos = (i + 1) / width
            if pct_pos <= 0.25:
                row += "🟩"
            elif pct_pos <= 0.50:
                row += "🟨"
            elif pct_pos <= 0.75:
                row += "🟧"
            else:
                row += "🟥"
        else:
            row += "⬛"
    return row


def mini_chart_bar(pct: float, width: int = 6) -> str:
    """Mini chart bar for inline use: shows blocks in gradient."""
    filled = round((pct / 100) * width)
    filled = min(filled, width)
    parts = []
    for i in range(width):
        if i < filled:
            ratio_pos = (i + 1) / width
            if ratio_pos <= 0.33:
                parts.append("🟩")
            elif ratio_pos <= 0.66:
                parts.append("🟨")
            else:
                parts.append("🟥")
        else:
            parts.append("⬛")
    return "".join(parts)


def build_traffic_embed(servers: list) -> discord.Embed:
    """Build a traffic embed with a full gradient chart style — servers displayed as
       horizontal colored bar charts showing capacity visually."""
    servers = sorted(servers, key=lambda s: s.get("displayorder", 999))

    ets2 = [s for s in servers if s.get("game") == "ETS2"]
    ats = [s for s in servers if s.get("game") == "ATS"]

    total_ets2 = sum(s.get("players", 0) for s in ets2)
    total_ats = sum(s.get("players", 0) for s in ats)
    total_players = total_ets2 + total_ats

    # ---- Header ----
    total_pct = total_ets2 + total_ats
    total_max = sum(s.get("maxplayers", 0) for s in servers)
    total_pct_val = (total_pct / total_max * 100) if total_max else 0

    overall_chart = gradient_chart(total_pct, total_max, 10)

    header = (
        f"🌍 **ETS2** {total_ets2:,} drivers　|　🇺🇸 **ATS** {total_ats:,} drivers\n"
        f"{overall_chart}　**{total_players:,}** online"
    )

    embed = discord.Embed(
        title="🚛 TruckersMP Server Traffic",
        description=header,
        color=GRADIENT_COLOR,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=config.AVATAR_URL)

    # ---- Gradient Legend ----
    legend = "🟩 Low 　 🟨 Medium 　 🟧 High 　 🟥 Full"
    embed.add_field(name="📊 **Capacity Gradient**", value=legend, inline=False)

    # ---- ETS2 Server Chart ----
    ets2_lines = []
    for s in ets2:
        players = s.get("players", 0)
        maxp = s.get("maxplayers", 0)
        pct = (players / maxp * 100) if maxp else 0
        chart = gradient_chart(players, maxp, 10)
        status = "🟢" if s.get("online") else "🔴"
        name = s.get("shortname", s.get("name", "Unknown"))
        flag = "🎪" if (s.get("event") or s.get("specialEvent")) else "　"

        ets2_lines.append(
            f"{status} {flag} **{name}**\n"
            f"`{chart}` `{players:>4}` / `{maxp:>4}` ({pct:3.0f}%)"
        )

    embed.add_field(
        name=f"🌍 **ETS2 Servers** ({sum(1 for s in ets2 if s.get('online'))}/{len(ets2)})",
        value="\n".join(ets2_lines) if ets2_lines else "No servers",
        inline=False
    )

    # ---- ATS Server Chart ----
    ats_lines = []
    for s in ats:
        players = s.get("players", 0)
        maxp = s.get("maxplayers", 0)
        pct = (players / maxp * 100) if maxp else 0
        chart = gradient_chart(players, maxp, 10)
        status = "🟢" if s.get("online") else "🔴"
        name = s.get("shortname", s.get("name", "Unknown"))
        flag = "🎪" if (s.get("event") or s.get("specialEvent")) else "　"

        ats_lines.append(
            f"{status} {flag} **{name}**\n"
            f"`{chart}` `{players:>4}` / `{maxp:>4}` ({pct:3.0f}%)"
        )

    embed.add_field(
        name=f"🇺🇸 **ATS Servers** ({sum(1 for s in ats if s.get('online'))}/{len(ats)})",
        value="\n".join(ats_lines) if ats_lines else "No servers",
        inline=False
    )

    # ---- Speed / Collisions summary table ----
    detail_lines = []

    def get_server_flag(s):
        if s.get("specialEvent"):
            return "🎪"
        if s.get("event"):
            return "📅"
        return "　"

    # Show top 5 servers quick info
    top_by_players = sorted(servers, key=lambda s: s.get("players", 0), reverse=True)
    for s in top_by_players[:6]:
        name = s.get("shortname", s.get("name", "Unknown"))
        players = s.get("players", 0)
        maxp = s.get("maxplayers", 0)
        pct = (players / maxp * 100) if maxp else 0
        bar = mini_chart_bar(pct, 6)
        sl = "🔇" if s.get("speedlimiter") else "🔊"
        col = "💥" if s.get("collisions") else "🚫"
        cars = "🚗" if s.get("carsforplayers") else "🚛"
        flag = get_server_flag(s)
        detail_lines.append(
            f"`{bar}` {flag} **{name}** — {sl} {col} {cars}　`{players:,}` drivers"
        )

    embed.add_field(
        name="⚙️ **Server Details** (Speed·Coll·Cars)",
        value="\n".join(detail_lines) if detail_lines else "No data",
        inline=False
    )

    embed.set_footer(
        text=f"{config.FOOTER_TEXT} • Traffic Live | Updated",
        icon_url=config.FOOTER_ICON
    )

    return embed


class TrafficCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_unload(self):
        self.auto_traffic.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.auto_traffic.start()

    @tasks.loop(hours=1)
    async def auto_traffic(self):
        """Automatically post traffic status every 1 hour to the traffic channel."""
        channel = self.bot.get_channel(TRAFFIC_CHANNEL_ID)
        if not channel:
            print("[Traffic] Traffic channel not found.")
            return

        servers = await fetch_servers()
        if not servers:
            print("[Traffic] Failed to fetch servers for auto-post.")
            return

        embed = build_traffic_embed(servers)
        try:
            async for msg in channel.history(limit=5):
                if msg.author == self.bot.user and msg.embeds:
                    await msg.delete()
                    break
        except Exception:
            pass

        await channel.send(embed=embed)

    @auto_traffic.before_loop
    async def before_auto_traffic(self):
        await self.bot.wait_until_ready()


@app_commands.command(name="traffic", description="Show current TruckersMP server traffic status")
async def traffic_command(interaction: discord.Interaction):
    """Slash command to view live TMP server traffic."""
    await interaction.response.defer()

    servers = await fetch_servers()

    if not servers:
        await interaction.followup.send("❌ Failed to fetch TruckersMP server data. Please try again later.")
        return

    embed = build_traffic_embed(servers)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="TruckersMP Servers",
        style=discord.ButtonStyle.link,
        url="https://truckersmp.com/status"
    ))

    await interaction.followup.send(embed=embed, view=view)