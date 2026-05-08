import os
import json
import time
import requests
import validators
import discord
from discord.ext import commands
from discord.ui import View, Modal, InputText
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SMM_API_KEY = os.getenv("SMM_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

API_URL = "https://cheapestsmmpanels.com/api/v2"
SERVICE_ID = 3080
QUANTITY = 100

COOLDOWN_SECONDS = 1800  # 30 mins

SETTINGS_FILE = "settings.json"
COOLDOWN_FILE = "cooldowns.json"

intents = discord.Intents.default()

bot = commands.Bot(intents=intents)


# =========================
# SETTINGS
# =========================

def load_settings():

    if not os.path.exists(SETTINGS_FILE):

        default = {
            "keys_enabled": True
        }

        with open(SETTINGS_FILE, "w") as f:
            json.dump(default, f)

        return default

    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


def save_settings(data):

    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# COOLDOWNS
# =========================

def load_cooldowns():

    if not os.path.exists(COOLDOWN_FILE):

        with open(COOLDOWN_FILE, "w") as f:
            json.dump({}, f)

        return {}

    with open(COOLDOWN_FILE, "r") as f:
        return json.load(f)


def save_cooldowns(data):

    with open(COOLDOWN_FILE, "w") as f:
        json.dump(data, f, indent=4)


def check_cooldown(user_id):

    cooldowns = load_cooldowns()

    user_id = str(user_id)

    if user_id not in cooldowns:
        return 0

    last_used = cooldowns[user_id]

    remaining = COOLDOWN_SECONDS - (time.time() - last_used)

    if remaining <= 0:
        return 0

    return int(remaining)


def update_cooldown(user_id):

    cooldowns = load_cooldowns()

    cooldowns[str(user_id)] = time.time()

    save_cooldowns(cooldowns)


# =========================
# KEY SYSTEM
# =========================

def load_keys():

    if not os.path.exists("keys.txt"):
        return []

    with open("keys.txt", "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def remove_key(key):

    keys = load_keys()

    if key in keys:

        keys.remove(key)

        with open("keys.txt", "w") as f:

            for k in keys:
                f.write(k + "\n")


# =========================
# MODAL
# =========================

class OrderModal(Modal):

    def __init__(self):

        super().__init__(title="Kalu")

        settings = load_settings()

        self.video_link = InputText(
            label="Video Link",
            placeholder="https://example.com/video",
            required=True
        )

        self.amount = InputText(
            label="Amount",
            value="100",
            required=True
        )

        self.add_item(self.video_link)
        self.add_item(self.amount)

        if settings["keys_enabled"]:

            self.key_input = InputText(
                label="Key",
                placeholder="Enter your 5-character key",
                required=True,
                min_length=5,
                max_length=5
            )

            self.add_item(self.key_input)

    async def callback(self, interaction: discord.Interaction):

        user_id = interaction.user.id

        # =========================
        # COOLDOWN CHECK
        # =========================

        remaining = check_cooldown(user_id)

        if remaining > 0:

            minutes = remaining // 60
            seconds = remaining % 60

            await interaction.response.send_message(
                f"❌ Cooldown active.\nTry again in {minutes}m {seconds}s.",
                ephemeral=True
            )

            return

        settings = load_settings()

        link = self.video_link.value.strip()
        amount = self.amount.value.strip()

        # =========================
        # URL VALIDATION
        # =========================

        if not validators.url(link):

            await interaction.response.send_message(
                "❌ Invalid video link.",
                ephemeral=True
            )

            return

        # =========================
        # AMOUNT VALIDATION
        # =========================

        if amount != "100":

            await interaction.response.send_message(
                "❌ Amount must be 100.",
                ephemeral=True
            )

            return

        # =========================
        # KEY VALIDATION
        # =========================

        if settings["keys_enabled"]:

            user_key = self.key_input.value.strip()

            valid_keys = load_keys()

            if user_key not in valid_keys:

                await interaction.response.send_message(
                    "❌ Key is invalid or expired.",
                    ephemeral=True
                )

                return

            remove_key(user_key)

        # =========================
        # API ORDER
        # =========================

        try:

            payload = {
                "key": SMM_API_KEY,
                "action": "add",
                "service": SERVICE_ID,
                "link": link,
                "quantity": QUANTITY
            }

            response = requests.post(
                API_URL,
                data=payload,
                timeout=30
            )

            data = response.json()

            # Update cooldown
            update_cooldown(user_id)

            # Success message
            await interaction.response.send_message(
                f"✅ Order placed successfully.\nAPI Response: `{data}`",
                ephemeral=True
            )

            # =========================
            # LOGS
            # =========================

            log_channel = bot.get_channel(LOG_CHANNEL_ID)

            if log_channel:

                embed = discord.Embed(
                    title="New Order Placed",
                    color=discord.Color.green()
                )

                embed.add_field(
                    name="User",
                    value=f"{interaction.user} ({interaction.user.id})",
                    inline=False
                )

                embed.add_field(
                    name="Video Link",
                    value=link,
                    inline=False
                )

                embed.add_field(
                    name="Quantity",
                    value=str(QUANTITY),
                    inline=False
                )

                embed.add_field(
                    name="Keys Required",
                    value=str(settings["keys_enabled"]),
                    inline=False
                )

                embed.add_field(
                    name="API Response",
                    value=f"```{data}```",
                    inline=False
                )

                await log_channel.send(embed=embed)

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Failed to place order.\n```{e}```",
                ephemeral=True
            )


# =========================
# BUTTON VIEW
# =========================

class TicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Get Views",
        style=discord.ButtonStyle.primary,
        emoji="✅"
    )
    async def kalu_button(self, button, interaction):

        await interaction.response.send_modal(
            OrderModal()
        )


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    try:

        synced = await bot.sync_commands()

        print(f"Synced {len(synced)} commands")

    except Exception as e:
        print(e)


# =========================
# COMMANDS
# =========================

@bot.slash_command(
    name="jstock",
    description="Shows stock"
)
async def jstock(ctx):

    await ctx.respond(
        "💰 860k Credits"
    )


@bot.slash_command(
    name="jsetup",
    description="Setup panel"
)
async def jsetup(ctx):

    if ctx.author.id != OWNER_ID:

        await ctx.respond(
            "❌ Only owner can use this command.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="TikTok Views Tool",
        description="Click the button below to get free TikTok Views",
        color=discord.Color.green()
    )

    embed.set_footer(
        text="Powered by CodeNest System"
    )

    await ctx.channel.send(
        embed=embed,
        view=TicketView()
    )

    await ctx.respond(
        "✅ Setup completed.",
        ephemeral=True
    )


# =========================
# ENABLE / DISABLE KEYS
# =========================

@bot.slash_command(
    name="jkeys",
    description="Enable or disable keys"
)
async def jkeys(
    ctx,
    mode: discord.Option(
        str,
        choices=["enable", "disable"]
    )
):

    if ctx.author.id != OWNER_ID:

        await ctx.respond(
            "❌ Only owner can use this command.",
            ephemeral=True
        )

        return

    settings = load_settings()

    if mode == "enable":

        settings["keys_enabled"] = True

        save_settings(settings)

        await ctx.respond(
            "✅ Keys have been ENABLED."
        )

    else:

        settings["keys_enabled"] = False

        save_settings(settings)

        await ctx.respond(
            "✅ Keys have been DISABLED."
        )


bot.run(TOKEN)
