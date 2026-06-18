# NepPath GA (General Availability) - Virtual Trucking Company Assistant

NepPath GA is the full-version, feature-rich Discord assistant designed specifically for Virtual Trucking Companies (VTCs) on TruckersMP. This final release provides a stable and professional solution for automating administrative workflows, event coordination, and community engagement.

## 🚀 Final Release Features

###  Advanced Music System
- **Command:** `/np [link] not beable to play, it is test only {Administer}`
- **Features:** Supports YouTube, SoundCloud, and Playlists.
- **Architecture:** Implements per-server independent queues and stable FFmpeg streaming.

### 🎂 Birthday Registry
- **Command:** `/birthday-setup` and `/dobtest`
- **Features:** Users can register their DOB (DD/MM/YYYY). The bot automatically sends a beautiful announcement with an animated banner in the configured channel on their special day.

### 🎙️ Voice Master (Join to Create)
- **Channel:** Connect to the Master VC.
- **Features:** Automatically creates a temporary voice channel, moves the user, and pings them with a button to rename their new room via a popup modal.

### 🔐 Enhanced Ticket Privacy
- **Logic:** Tickets created for Partnership, Support, CEO, or Founders are now locked down with explicit permission overwrites. Only the opener, the bot, and relevant management roles can see the content.
- **Categories:** Automated routing to the Management Ticket Category ID.

## 🔮 Future Roadmap
We are continuously looking to expand NepPath's capabilities. Future updates will include:
- **Advanced Analytics Dashboard:** Visual representations of VTC growth and member activity.
- **Expanded TMP API Integration:** Real-time location tracking and automated job logging.
- **Multi-Language Support:** Localized commands for global VTC branches.
- **Economy System:** A custom VTC currency and shop system for driver rewards.

## 🛠️ Setup

1. **Environment Variables**: Create a `.env` file with your `DISCORD_TOKEN`.
2. **Config**: Update `config.py` with your server's Role IDs and Channel IDs.
3. **Dependencies**:
   ```bash
   pip install discord.py yt-dlp PyNaCl aiohttp python-dotenv Pillow
   ```
4. **FFmpeg**: Ensure FFmpeg is installed and added to your system's PATH for Music/Sound features.

## 📜 Key Features
- **TruckersMP Integration**: Scrapes event data and VTC stats directly from the API.
- **Event Booking**: `/book` creates interactive slot booking maps for convoys.
- **Role Management**: `/assign-role` and `/remove-role` with auto-logic for driver ranks.
- **Transcripts**: Automated HTML-style text transcripts when tickets are closed.

---
Developed for **NepPath VTC**.