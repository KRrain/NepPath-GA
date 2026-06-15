import discord
from discord import app_commands
from discord.ui import View, Button
import aiohttp
from bs4 import BeautifulSoup
import config
import re
from datetime import datetime
from discord.ext import commands

TARGET_URL = config.TARGET_URL

# ================= MODAL =================
class UpcomingModal(discord.ui.Modal, title="Upcoming Event Checker"):
    event_date = discord.ui.TextInput(
        label="Event Date",
        placeholder="Dec 24, 2025",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Flexible Date Parsing
        user_input = self.event_date.value.strip()
        search_dates = {user_input}

        # Clean input (remove ordinal suffixes like st, nd, rd, th)
        clean_input = re.sub(r'(?<=\d)(st|nd|rd|th)', '', user_input, flags=re.IGNORECASE)
        
        # Try parsing various formats
        dt = None
        formats = [
            "%b %d, %Y", "%B %d, %Y",       # Dec 24, 2025
            "%b %d %Y", "%B %d %Y",         # Dec 24 2025
            "%d %b %Y", "%d %B %Y",         # 24 Dec 2025
            "%d %b, %Y", "%d %B, %Y",       # 24 Dec, 2025
            "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(clean_input.title(), fmt)
                break
            except ValueError:
                continue
        
        if dt:
            # Add common formats found on websites
            search_dates.add(dt.strftime("%d %b %Y"))      # 30 May 2026
            search_dates.add(dt.strftime("%B %d, %Y"))     # May 30, 2026
            search_dates.add(dt.strftime("%Y-%m-%d"))      # 2026-05-30

        page = 1
        events_found = []

        async with aiohttp.ClientSession() as session:
            while True:
                url = f"{TARGET_URL}?page={page}"
                async with session.get(url) as resp:
                    html = await resp.text()

                soup = BeautifulSoup(html, "html.parser")
                cards = soup.find_all(
                    "div",
                    class_="col-md-4 col-sm-12 col-xs-12 mx-auto mb-5"
                )

                if not cards:
                    break  # no more events

                for card in cards:
                    text = card.get_text(" ", strip=True)
                    if any(d in text for d in search_dates):
                        # Extract event title
                        event_title_tag = card.find("h3")
                        event_title = event_title_tag.text if event_title_tag else "Upcoming Event"

                        # Extract VTC name (usually in a <h4> or <a> inside card, adjust if needed)
                        vtc_tag = card.find("h4") or card.find("a")
                        vtc_name = vtc_tag.text.strip() if vtc_tag else "Unknown VTC"

                        # Extract description
                        desc_tag = card.find("p")
                        description = desc_tag.text if desc_tag else text

                        # Extract link
                        link_tag = card.find("a", href=True)
                        link = link_tag['href'] if link_tag else TARGET_URL
                        
                        if link.startswith("/"):
                            link = f"https://truckersmp.com{link}"

                        events_found.append({
                            "vtc_name": vtc_name,
                            "event_title": event_title,
                            "description": description,
                            "url": link
                        })

                if events_found:
                    break

                page += 1  # next page
                if page > 10:
                    break

        if events_found:
            embed = discord.Embed(
                title=f"Events on {user_input}",
                description=f"Found {len(events_found)} event(s)",
                color=discord.Color.orange()
            )

            view = View()
            for idx, event in enumerate(events_found, start=1):
                embed.add_field(
                    name=f"{event['event_title']} ({event['vtc_name']})",
                    value=event['description'],
                    inline=False
                )
                
                label = f"{event['vtc_name']} - {event['event_title']}"
                if len(label) > 80:
                    label = label[:77] + "..."
                
                url = event['url']
                if len(url) > 512:
                    url = TARGET_URL
                view.add_item(Button(label=label, url=url))

            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(
                "❌ No event found for this date.",
                ephemeral=True
            )
# ================= COMMAND =================
def setup(bot: commands.Bot):

    @bot.tree.command(
        name="upcoming",
        description="Check upcoming events by date"
    )
    async def upcoming(interaction: discord.Interaction):
        await interaction.response.send_modal(UpcomingModal())