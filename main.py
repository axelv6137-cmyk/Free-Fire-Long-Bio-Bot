import os
import sys
import logging
import requests
from urllib.parse import urlparse, parse_qs, quote
import discord
from discord.ext import commands
from discord import Intents
from flask import Flask
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
API_KEY = os.getenv('API_KEY', '')
API_BASE_URL = 'https://bio.ffutils.tech/api/update_bio'
REQUIRED_ROLE = '' # Pon el ID del rol aquí. Vacío = cualquiera puede usarlo

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    sys.exit(1)

# Flask para mantener vivo el servicio en Render
app = Flask(__name__)
@app.route('/')
def home(): 
    return "FF Bio Discord Bot is running", 200

def extract_access_token(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith('http://') or raw.startswith('https://'):
        try:
            parsed = urlparse(raw)
            params = parse_qs(parsed.query)
            if 'eat' in params: return params['eat'][0]
            if 'access_token' in params: return params['access_token'][0]
        except Exception: pass
        return None
    if raw and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in raw):
        return raw
    return None

def call_bio_api(token: str, bio: str) -> dict:
    try:
        url = f"{API_BASE_URL}?access_token={token}&bio={quote(bio, safe='')}&key={API_KEY}"
        resp = requests.get(url, timeout=15)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def check_role(ctx):
    if REQUIRED_ROLE == '': return True
    role = discord.utils.get(ctx.author.roles, id=int(REQUIRED_ROLE))
    return role is not None

@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Game(name="!bio para cambiar bio"))

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Bot activo")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 FF Bio Updater Bot", color=0x00ff00)
    embed.add_field(name="Uso", value="`!bio <access_token> <nueva bio>`", inline=False)
    embed.add_field(name="Token válido", value="• Token plano\n• Link Kiosgamer\n• Link Garena Help", inline=False)
    embed.add_field(name="Ejemplo", value="`!bio d8a4e0bd68fb FREE FIRE PRO ⚡`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def bio(ctx, token_raw: str = None, *, bio_text: str = None):
    if not await check_role(ctx):
        return await ctx.send("❌ No tienes permisos para usar este comando")
        
    if not token_raw or not bio_text:
        await ctx.send("❌ Formato incorrecto!\nUsa: `!bio <token> <nueva bio>`\nEscribe `!help` para más info")
        return

    token = extract_access_token(token_raw)
    if token is None:
        await ctx.send("❌ Token inválido!\nDebe ser token plano o link de Kiosgamer/Garena")
        return

    msg = await ctx.send("⏳ Actualizando tu bio, espera...")
    result = call_bio_api(token, bio_text)
    await msg.delete()

    if result.get('status') == 'success':
        embed = discord.Embed(title="✅ Bio actualizada!", color=0x00ff00)
        embed.add_field(name="👤 Player", value=f"`{result.get('nickname', 'Unknown')}`", inline=True)
        embed.add_field(name="🆔 UID", value=f"`{result.get('uid', 'N/A')}`", inline=True)
        embed.add_field(name="📱 Platform", value=f"`{result.get('platform', 'N/A')}`", inline=True)
        embed.add_field(name="🌍 Region", value=f"`{result.get('region', 'N/A')}`", inline=True)
        embed.add_field(name="📝 Nueva Bio", value=result.get('bio', bio_text), inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Error al actualizar!\n🔴 {result.get('message', 'Error desconocido')}")

def run_bot():
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    # Correr bot y flask al mismo tiempo
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
