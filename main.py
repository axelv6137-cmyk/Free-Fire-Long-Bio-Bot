import os
import sys
import logging
import threading
import requests
from urllib.parse import urlparse, parse_qs, quote
import discord
from discord.ext import commands
from flask import Flask

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
API_KEY = os.getenv('API_KEY', '')
API_BASE_URL = 'https://bio.ffutils.tech/api/update_bio'
OWNER_USERNAME = '' # Pon tu @ de Discord aquí. Ej: '@axelv'
REQUIRED_ROLE = '' # Pon el ID del rol. Vacío = cualquiera

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    sys.exit(1)

app = Flask(__name__)
@app.route('/')
def index():
    return {'status': 'running', 'bot': 'FF Bio Updater Discord'}, 200

def extract_access_token(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith('http://') or raw.startswith('https://'):
        try:
            params = parse_qs(urlparse(raw).query)
            if 'eat' in params: return params['eat'][0]
            if 'access_token' in params: return params['access_token'][0]
        except: pass
        return None
    if raw and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in raw):
        return raw
    return None

def call_bio_api(token: str, bio: str) -> dict:
    try:
        url = f"{API_BASE_URL}?access_token={token}&bio={quote(bio, safe='')}&key={API_KEY}"
        return requests.get(url, timeout=15).json()
    except: return {"status": "error", "message": "Error de conexion"}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user}")

@bot.command()
async def help(ctx):
    await ctx.send("📖 Usa: `!bio <token> <nueva bio>`\nEjemplo: `!bio d8a4e0bd68fb PRO ⚡`")

@bot.command()
async def bio(ctx, token_raw: str = None, *, bio_text: str = None):
    if not token_raw or not bio_text:
        return await ctx.send("❌ Usa: `!bio <token> <nueva bio>`")
    
    token = extract_access_token(token_raw)
    if not token: return await ctx.send("❌ Token inválido")
    
    msg = await ctx.send("⏳ Actualizando...")
    result = call_bio_api(token, bio_text)
    await msg.delete()
    
    if result.get('status') == 'success':
        await ctx.send(f"✅ Bio actualizada!\n👤 `{result.get('nickname')}`\n🆔 `{result.get('uid')}`")
    else:
        await ctx.send(f"❌ Error: {result.get('message')}")

def run_bot():
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
