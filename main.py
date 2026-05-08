import os

    @discord.ui.button(
        label="Kalu",
        style=discord.ButtonStyle.primary,
        emoji="📩"
    )
    async def kalu_button(self, button, interaction):
        await interaction.response.send_modal(OrderModal())


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

@bot.slash_command(name="jstock", description="Shows stock")
async def jstock(ctx):
    await ctx.respond("💰 860k Credits")


@bot.slash_command(name="jsetup", description="Setup panel")
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

    embed.set_footer(text="Powered by Lalu System")

    await ctx.channel.send(
        embed=embed,
        view=TicketView()
    )

    await ctx.respond(
        "✅ Setup completed.",
        ephemeral=True
    )


bot.run(TOKEN)