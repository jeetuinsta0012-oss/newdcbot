import os
import json
import time
import requests
import validators
import discord

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ================= ENV =================

TOKEN = os.getenv("DISCORD_TOKEN")
SMM_API_KEY = os.getenv("SMM_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

API_URL = "https://cheapestsmmpanels.com/api/v2"

# ================= CONFIG =================

COOLDOWN_SECONDS = 1800

SERVICES = {
    "views": {
        "service_id": 3080,
        "quantity": 100,
        "keys_file": "keys.txt",
        "button_label": "Get Views",
        "button_style": discord.ButtonStyle.primary
    },

    "kaddu1": {
        "service_id": 3154,
        "quantity": 500,
        "keys_file": "kaddu1_keys.txt",
        "button_label": "Get Likes",
        "button_style": discord.ButtonStyle.success
    },

    "kaddu2": {
        "service_id": 3976,
        "quantity": 100,
        "keys_file": "kaddu2_keys.txt",
        "button_label": "Get Followers",
        "button_style": discord.ButtonStyle.danger
    }
}

SETTINGS_FILE = "settings.json"
COOLDOWN_FILE = "cooldowns.json"

# ================= BOT =================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ================= SETTINGS =================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default = {
            "keys_enabled": True
        }

        with open(SETTINGS_FILE, "w") as f:
            json.dump(default, f, indent=4)

        return default

    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

settings = load_settings()

# ================= COOLDOWNS =================

def load_cooldowns():
    if not os.path.exists(COOLDOWN_FILE):
        with open(COOLDOWN_FILE, "w") as f:
            json.dump({}, f)

    with open(COOLDOWN_FILE, "r") as f:
        return json.load(f)

cooldowns = load_cooldowns()

def save_cooldowns():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(cooldowns, f, indent=4)

def check_cooldown(user_id):
    now = int(time.time())

    if user_id not in cooldowns:
        return 0

    expire_time = cooldowns[user_id] + COOLDOWN_SECONDS

    if now >= expire_time:
        return 0

    return expire_time - now

def update_cooldown(user_id):
    cooldowns[user_id] = int(time.time())
    save_cooldowns()

# ================= KEYS =================

def load_keys(file_name):
    if not os.path.exists(file_name):
        open(file_name, "w").close()

    with open(file_name, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def remove_key(file_name, used_key):
    keys = load_keys(file_name)

    with open(file_name, "w") as f:
        for key in keys:
            if key != used_key:
                f.write(key + "\n")

# ================= MODAL =================

class OrderModal(discord.ui.Modal):

    def __init__(self, service_type):

        self.service_type = service_type
        self.service_data = SERVICES[service_type]

        super().__init__(
            title=f"{self.service_data['button_label']} Order"
        )

        self.link = discord.ui.InputText(
            label="TikTok Video Link",
            placeholder="https://www.tiktok.com/...",
            required=True
        )

        self.key = discord.ui.InputText(
            label="Key",
            placeholder="Enter your key",
            required=True,
            min_length=5,
            max_length=100
        )

        self.add_item(self.link)
        self.add_item(self.key)

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        remaining = check_cooldown(user_id)

        if remaining > 0:
            mins = remaining // 60
            secs = remaining % 60

            return await interaction.response.send_message(
                f"⏳ Cooldown active.\nTry again in {mins}m {secs}s",
                ephemeral=True
            )

        link = self.link.value.strip()
        user_key = self.key.value.strip()

        # ================= URL VALIDATION =================

        if not validators.url(link):
            return await interaction.response.send_message(
                "❌ Invalid URL",
                ephemeral=True
            )

        if "tiktok.com" not in link.lower():
            return await interaction.response.send_message(
                "❌ Only TikTok links are allowed",
                ephemeral=True
            )

        # ================= KEY VALIDATION =================

        keys_file = self.service_data["keys_file"]

        valid_keys = load_keys(keys_file)

        if user_key not in valid_keys:
            return await interaction.response.send_message(
                "❌ Invalid key for this service",
                ephemeral=True
            )

        # ================= API REQUEST =================

        payload = {
            "key": SMM_API_KEY,
            "action": "add",
            "service": self.service_data["service_id"],
            "link": link,
            "quantity": self.service_data["quantity"]
        }

        try:

            response = requests.post(
                API_URL,
                data=payload,
                timeout=20
            )

            data = response.json()

            # ================= API VALIDATION =================

            if "order" not in data:
                return await interaction.response.send_message(
                    f"❌ API Error\n```{data}```",
                    ephemeral=True
                )

            # ================= REMOVE KEY =================

            remove_key(keys_file, user_key)

            # ================= UPDATE COOLDOWN =================

            update_cooldown(user_id)

            # ================= SUCCESS MESSAGE =================

            await interaction.response.send_message(
                f"✅ Order placed successfully!\n\n"
                f"📦 Service: {self.service_type}\n"
                f"🔢 Quantity: {self.service_data['quantity']}\n"
                f"🆔 Order ID: {data['order']}",
                ephemeral=True
            )

            # ================= LOGS =================

            log_channel = bot.get_channel(LOG_CHANNEL_ID)

            if log_channel:

                embed = discord.Embed(
                    title="📦 New Order",
                    color=discord.Color.green()
                )

                embed.add_field(
                    name="User",
                    value=interaction.user.mention,
                    inline=False
                )

                embed.add_field(
                    name="Button",
                    value=self.service_type,
                    inline=True
                )

                embed.add_field(
                    name="Quantity",
                    value=str(self.service_data["quantity"]),
                    inline=True
                )

                embed.add_field(
                    name="Service ID",
                    value=str(self.service_data["service_id"]),
                    inline=True
                )

                embed.add_field(
                    name="Link",
                    value=link,
                    inline=False
                )

                embed.add_field(
                    name="Order ID",
                    value=str(data["order"]),
                    inline=False
                )

                await log_channel.send(embed=embed)

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Error:\n```{e}```",
                ephemeral=True
            )

# ================= BUTTON VIEW =================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Get Views",
        style=discord.ButtonStyle.primary,
        custom_id="views_button"
    )
    async def views_button(self, button, interaction):
        await interaction.response.send_modal(
            OrderModal("views")
        )

    @discord.ui.button(
        label="TikTok Likes",
        style=discord.ButtonStyle.success,
        custom_id="kaddu1_button"
    )
    async def kaddu1_button(self, button, interaction):
        await interaction.response.send_modal(
            OrderModal("kaddu1")
        )

    @discord.ui.button(
        label="TikTok Followers",
        style=discord.ButtonStyle.danger,
        custom_id="kaddu2_button"
    )
    async def kaddu2_button(self, button, interaction):
        await interaction.response.send_modal(
            OrderModal("kaddu2")
        )

# ================= EVENTS =================

@bot.event
async def on_ready():

    bot.add_view(TicketView())

    print(f"Logged in as {bot.user}")

# ================= COMMANDS =================

@bot.slash_command(name="jsetup")
async def jsetup(ctx):

    if ctx.author.id != OWNER_ID:
        return await ctx.respond(
            "❌ Owner only command",
            ephemeral=True
        )

    embed = discord.Embed(
        title="TikTok Views Tool",
        description="Click the buttons below to get TikTok Services",
        color=discord.Color.green()
    )

    embed.set_footer(
        text="Powered by CodeNest System"
    )

    await ctx.respond(
        embed=embed,
        view=TicketView()
    )

@bot.slash_command(name="jstock")
async def jstock(ctx):

    await ctx.respond(
        "💰 Stock Available"
    )

# ================= START =================

bot.run(TOKEN)
