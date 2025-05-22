import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from keep_alive import keep_alive

# keep_alive を呼び出して Flask サーバーを起動
keep_alive()

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_GUILD_ID = int(os.getenv("TARGET_GUILD_ID"))

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "data.json"
last_counts = {"members": 0, "bots": 0}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(status=discord.Status.invisible)
    await tree.sync(guild=discord.Object(id=TARGET_GUILD_ID))


@tree.command(name="setcategory", description="カテゴリを指定して自動的に人数表示チャンネルを作成", guild=discord.Object(id=TARGET_GUILD_ID))
@app_commands.describe(category="チャンネルを作成するカテゴリ")
async def setcategory(interaction: discord.Interaction, category: discord.CategoryChannel):
    if interaction.guild.id != TARGET_GUILD_ID:
        await interaction.response.send_message("このサーバーでは使えません。", ephemeral=True)
        return

    # 管理者チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    # チャンネル作成
    bot_channel = await category.create_voice_channel(name="🤖 Bots: 0")
    member_channel = await category.create_voice_channel(name="👥 Members: 0")

    # 保存
    data = {
        "bot_channel_id": bot_channel.id,
        "member_channel_id": member_channel.id
    }
    save_data(data)

    await interaction.response.send_message(
        f"✅ チャンネルを作成しました！\n- {bot_channel.mention}\n- {member_channel.mention}"
    )

    # 初期更新
    await update_counts(interaction.guild)


@bot.event
async def on_member_join(member):
    await update_counts(member.guild)


@bot.event
async def on_member_remove(member):
    await update_counts(member.guild)


async def update_counts(guild):
    if guild.id != TARGET_GUILD_ID:
        return

    data = load_data()
    bot_channel = guild.get_channel(data.get("bot_channel_id"))
    member_channel = guild.get_channel(data.get("member_channel_id"))

    if not bot_channel or not member_channel:
        return

    members = guild.members
    bot_count = sum(1 for m in members if m.bot)
    member_count = len(members)

    global last_counts
    if bot_count == last_counts["bots"] and member_count == last_counts["members"]:
        return  # 変化なし

    last_counts["bots"] = bot_count
    last_counts["members"] = member_count

    await bot_channel.edit(name=f"🤖 Bots: {bot_count}")
    await member_channel.edit(name=f"👥 Members: {member_count}")


bot.run(TOKEN)
