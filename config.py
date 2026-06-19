from pathlib import Path
import json

# ================== ROLES ==================
# Set this to your Server ID to update commands instantly on restart
GUILD_ID = 1395555672946643005



VTC_ID = 81586
HR_ROLE_ID = 1395699038715642031
MANAGER_ROLE_ID = 1395579347804487769
RECRUITMENT_ROLE_ID = 1430486391774511224
CEO_ROLE_ID = 1395581301704364072
FOUNDER_ROLE_ID = 1395578532406624266
EVENT_MANAGER_ROLE_ID = 1395580379565527110
PING_ROLE_ID = 1398294285597671606
DRIVER_ROLE_ID = 1398294285597671606
PARTNER_ROLE_ID = 1396314109011693750
COMMUNITY_MEMBERS_ROLE_ID = 1412162444855349460
MEDIA_ROLE_ID = 1436382728168669344

# Staff Roles (List of IDs)
STAFF_ROLE_ID = [1395582132830601296, 449953584549986317]

AUTHORIZED_ASSIGN_ROLES = [
    HR_ROLE_ID,
    MANAGER_ROLE_ID,
    RECRUITMENT_ROLE_ID,
    CEO_ROLE_ID,
    FOUNDER_ROLE_ID,
    EVENT_MANAGER_ROLE_ID,
]

# fill vtc modal authorized roles
FILL_VTC_AUTHORIZED_ROLES = [
    HR_ROLE_ID,
    MANAGER_ROLE_ID,
    CEO_ROLE_ID,
    FOUNDER_ROLE_ID,
    EVENT_MANAGER_ROLE_ID,
    PARTNER_ROLE_ID,
]

# ================== CHANNELS ==================
STAFF_LOG_CHANNEL_ID = 1446383730242355200
CATEGORY_TICKET_ID = 1395740745280917625
MANAGEMENT_TICKET_CATEGORY_ID = 1444275592018133155
TRANSCRIPT_CHANNEL_ID = 1413068675707174912
STARBOARD_LOG_CHANNEL_ID = 1443774139885424812
MARK_ATTENDEES_CHANNEL_ID = 1396109795370471424 # Channel where attendees can mark themselves present
# Markdown guide channel
MAEK_DOWN_CHANNEL = "https://discord.com/channels/1395555672946643005/1396109795370471424"
PARTNERSHIP_CHANNEL_ID = 1455383683786866759
PARTNERSHIP_RESULT_CHANNEL_ID = 1455409070260621355
ROLE_REQUEST_CATEGORY_ID = 1444276048710860810
UPDATE_ROLES_CHANNEL_ID = 1457880114724343975
UPDATE_ROLES_CHANNEL_IMAGE_URL = "https://i.imgur.com/FR7ixdV.gif"
# Birthday Channels
BIRTHDAY_FILL_CHANNEL_ID = 1515910417388409053
BIRTHDAY_ANNOUNCE_CHANNEL_ID = 1515910773380223136
# Voice Master
VOICE_MASTER_CHANNEL_ID = 1515921785743478836
# Traffic
TRAFFIC_CHANNEL_ID = 1517437927435800661
# ================== VISUALS ==================
EMBED_COLOR = 0xFF5A20
AVATAR_URL = "https://i.imgur.com/wxH9Mob.png"
FOOTER_TEXT = "NepPath"
FOOTER_ICON = "https://i.imgur.com/qmiah0r.gif"
BIRTHDAY_BANNER_URL = "https://cdn.discordapp.com/attachments/1395811486596857896/1515919705565692004/Birthday.png?ex=6a30c1be&is=6a2f703e&hm=ddf9e47785ec6c397d45acfbe85b65ec0ca6cda3b37846e833bfaba6690bfc42&"

# ================== FILES ==================
DATA_FILE = Path("./data/data.json")
TICKET_RECORD_FILE = Path("./data/tickets.json")
BOOKING_JSON_FILE = "./data/bookings.json"
STARBOARD_CONFIG_FILE = Path("./data/starboard_config.json")
LEADERBOARD_FILE = Path("./data/leaderboard.json")
BIRTHDAY_FILE = Path("./data/birthdays.json")

# ================== URLS ==================
TARGET_URL = "https://truckersmp.com/vtc/81586/events/attending"
ROLE_REQUEST_FORM_URL = "https://cdn.discordapp.com/attachments/1395811486596857896/1412010490393268284/20250901_174512.png?ex=6955997e&is=695447fe&hm=a177f081948767120ce197ea9e0d5e578c7d4ccf2a85658b3be92e6a5ac466a5&"

def load_starboard_config():
    if not STARBOARD_CONFIG_FILE.exists():
        return {}
    try:
        with open(STARBOARD_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_starboard_config(data):
    STARBOARD_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STARBOARD_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_leaderboard():
    if not LEADERBOARD_FILE.exists():
        return {"guilds": {}}
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except:
        return {"guilds": {}}

def save_leaderboard(data):
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)
