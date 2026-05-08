import os
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

intents = discord.Intents.default()

bot = commands.Bot(intents=intents)


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

        self.key_input = InputText(
            label="Key",
            placeholder="Enter your 5-character key",
            required=True,
            min_length=5,
            max_length=5
        )

        self.add_item(self.video_link)
        self.add_item(self.amount)
        self.add_item(self.key_input)

    async def callback(self, interaction: discord.Interaction):

        link = self.video_link.value.strip()
        amount = self.amount.value.strip()
        user_key = self.key_input.value.strip()

        # Validate URL
        if not validators.url(link):
            await interaction.response.send_message(
                "❌ Invalid video link.",
                ephemeral=True
            )
            return

        # Amount locked
        if amount != "100":
            await interaction.response.send_message(
                "❌ Amount must be 100.",
                ephemeral=True
            )
            return

        # Validate key
        valid_keys = load_keys()

        if user_key not in valid_keys:
            await interaction.response.send_message(
                "❌ Key is invalid or expired.",
                ephemeral=True
            )
            return

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

            # Remove used key
            remove_key(user_key)

            # Success
            await interaction.response.send_message(
                f"✅ Order placed successfully.\nAPI Response: `{data}`",
                ephemeral=True
            )

            # Logs
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
        label="Kalu",
        style=discord.ButtonStyle.primary,
        emoji="📩"
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
        title="Lalu",
        description="Click the button below to continue.",
        color=discord.Color.green()
    )

    embed.set_footer(
        text="Powered by Lalu System"
    )

    await ctx.channel.send(
        embed=embed,
        view=TicketView()
    )

    await ctx.respond(
        "✅ Setup completed.",
        ephemeral=True
    )


bot.run(TOKEN)
