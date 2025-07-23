import os
from dotenv import load_dotenv  # optional, for local testing

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio

load_dotenv() 
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

OWNER_ID = 821565673456009236
TICKET_LOG_CHANNEL = "logs"
VOUCH_CHANNEL = "✅-vouches"

ticket_count = 0  # global counter for listed accounts

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.name}!")

@bot.event
async def on_member_join(member):
    guild = member.guild
    member_count = guild.member_count

    channel = discord.utils.get(guild.text_channels, name="👋-welcome")
    if channel:
        await channel.send(f"Welcome {member.mention} to the server! You are our {member_count}th member!")

    role = discord.utils.get(guild.roles, name="member")
    if role:
        try:
            await member.add_roles(role)
            print(f"Gave {member} the {role.name} role.")
        except discord.Forbidden:
            print(f"Missing permissions to assign role to {member}.")
        except Exception as e:
            print(f"Error assigning role: {e}")

class VouchModal(Modal, title="Submit an Anonymous Vouch"):
    price = TextInput(label="Price (numbers only)", max_length=10)
    account_type = TextInput(label="Account/Profile/Ironman", max_length=30)

    def __init__(self):
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        if not self.price.value.strip().isdigit():
            await interaction.response.send_message("Price must be a number.", ephemeral=True)
            return

        recipient = interaction.guild.get_member(OWNER_ID)
        message = f"**Anonymous Vouch** : +rep {interaction.user.mention} ${self.price.value.strip()} {self.account_type.value.strip()}"

        vouch_channel = discord.utils.get(interaction.guild.text_channels, name=VOUCH_CHANNEL)
        if vouch_channel:
            await vouch_channel.send(message)
        try:
            await recipient.send(message)
        except:
            pass

        await interaction.response.send_message("✅ Vouch submitted!", ephemeral=True)

class TicketControlView(View):
    def __init__(self, recipient):
        super().__init__(timeout=None)
        self.recipient = recipient

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_roles = [role.name.lower() for role in interaction.user.roles]
        if "owner" not in member_roles:
            await interaction.response.send_message("❌ You are not authorized to close this ticket.", ephemeral=True)
            return

        log_channel = discord.utils.get(interaction.guild.text_channels, name=TICKET_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(f"📁 Ticket {interaction.channel.name} closed by {interaction.user.mention}.")

        await interaction.response.send_message("Ticket will be closed.", ephemeral=True)
        await interaction.channel.delete()

    @discord.ui.button(label="Vouch", style=discord.ButtonStyle.primary)
    async def vouch(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_roles = [role.name.lower() for role in interaction.user.roles]
        if "owner" not in member_roles:
            await interaction.response.send_message("❌ If you want to anonymous vouch, ping an owner.", ephemeral=True)
            return

        await interaction.response.send_modal(VouchModal())
class BuyView(View):
    def __init__(self, listing_number, profile_link):
        super().__init__(timeout=None)
        self.listing_number = listing_number
        self.profile_link = profile_link

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="accounts")
        owner_role = discord.utils.get(guild.roles, name="owner")

        channel_name = f"💲ticket-{self.listing_number}-{interaction.user.name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        if owner_role:
            overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason="Purchase ticket created",
            category=category
        )

        mention_owner = f"||{owner_role.mention}||" if owner_role else ""
        await ticket_channel.send(
    f"{interaction.user.mention} has created a ticket to buy {self.profile_link}. {mention_owner}\n"
    f"{interaction.user.mention}, if you have any questions about the profile you may ask any of the owners.\n"
    f"For your convenience a skycrypt link to the account has been listed below:"
        )
        await ticket_channel.send(view=TicketControlView(interaction.user))
        await interaction.response.send_message("✅ Your purchase ticket has been created!", ephemeral=True)

    @discord.ui.button(label="Offer", style=discord.ButtonStyle.blurple)
    async def offer(self, interaction: discord.Interaction, button: discord.ui.Button):
        class OfferModal(Modal, title="Make an Offer"):
            offered_price = TextInput(label="Offered Price (numbers only)", placeholder="e.g. 500", max_length=10)
            payment_method = TextInput(label="Payment Method (max 10 characters)", placeholder="e.g. PayPal", max_length=10)

            async def on_submit(self_inner, interaction: discord.Interaction):
                if not self_inner.offered_price.value.strip().isdigit():
                    await interaction.response.send_message("❌ Offered price must be a number.", ephemeral=True)
                    return

                guild = interaction.guild
                category = discord.utils.get(guild.categories, name="accounts")
                owner_role = discord.utils.get(guild.roles, name="owner")

                channel_name = f"💲offer-{self_inner.offered_price.value.strip()}-{self_inner.payment_method.value.strip()}-{self.listing_number}"

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                if owner_role:
                    overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                ticket_channel = await guild.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    reason="Offer ticket created",
                    category=category
                )

                mention_owner = f"||{owner_role.mention}||" if owner_role else ""
                await ticket_channel.send(
                    f"{interaction.user.mention} has created a ticket to buy {self.profile_link}. ping {mention_owner}"
                    f"{interaction.user.mention}, if you have any questions about the profile you may ask any of the owners."
                    f"For your convenience a skycrypt link to the account has been listed below: {self.profile_link}"
                )
                await ticket_channel.send(view=TicketControlView(interaction.user))
                await interaction.response.send_message("✅ Your offer ticket has been created!", ephemeral=True)

        await interaction.response.send_modal(OfferModal())

@bot.tree.command(name="list", description="List a new account/profile for sale.")
@app_commands.describe(
    username="SkyCrypt username",
    price="Price",
    profile="Select the type of listing",
    profilename="Optional: SkyCrypt profile name"
)
@app_commands.choices(
    profile=[
        app_commands.Choice(name="Ironman", value="ironman"),
        app_commands.Choice(name="Island", value="island"),
        app_commands.Choice(name="Account", value="account")
    ]
)
async def list(
    interaction: discord.Interaction,
    username: str,
    price: str,
    profile: app_commands.Choice[str],
    profilename: str = None
):
    owner_role = discord.utils.get(interaction.guild.roles, name="owner")
    if owner_role not in interaction.user.roles:
        await interaction.response.send_message("❌ You must have the @owner role to use this command.", ephemeral=True)
        return

    global ticket_count
    ticket_count += 1

    guild = interaction.guild
    user = interaction.user

    emoji_map = {
        "ironman": "🤖",
        "island": "🏝️",
        "account": "🚹"
    }

    selected_profile = profile.value
    emoji = emoji_map.get(selected_profile, "")
    channel_name = f"{emoji}{price}-{selected_profile}-{ticket_count}"

    member_role = discord.utils.get(guild.roles, name="member")
    customer_role = discord.utils.get(guild.roles, name="customer")
    category = discord.utils.get(guild.categories, name="accounts")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if owner_role:
        overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if member_role:
        overwrites[member_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
    if customer_role:
        overwrites[customer_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        reason="New ticket listing",
        category=category
    )

    if profilename:
        link = f"https://sky.shiiyu.moe/stats/{username}/{profilename}"
    else:
        link = f"https://sky.shiiyu.moe/stats/{username}"

    view = BuyView(ticket_count, link)
    await ticket_channel.send(f"{user.mention} listed a profile!				 **Stats Link:** {link}", view=view)

bot.run(os.getenv("DISCORD_TOKEN"))