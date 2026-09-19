import os
import sys
import logging
import requests
import threading
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
REQUIRED_ROLE = '' # Pon el ID del rol requerido. Vacío = cualquiera

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    sys.exit(1)

# Flask para que Render no lo apague
app = Flask(__name__)
@app.route('/')
def index():
    return {'status': 'running', 'bot': 'FF Bio Updater Discord'}, 200

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

def extract_access_token(raw: str) -> str | None:
    """Extrae token de: token plano, link kiosgamer, link garena"""
    raw = raw.strip()

    if raw.startswith('http://') or raw.startswith('https://'):
        try:
            parsed = urlparse(raw)
            params = parse_qs(parsed.query)
            if 'eat' in params:
                return params['eat'][0]
            if 'access_token' in params:
                return params['access_token'][0]
        except Exception:
            pass
        return None

    if raw and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in raw):
        return raw

    return None

def call_bio_api(token: str, bio: str) -> dict:
    """Llama a la API de Free Fire"""
    try:
        url = f"{API_BASE_URL}?access_token={token}&bio={quote(bio, safe='')}&key={API_KEY}"
        resp = requests.get(url, timeout=15)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. Intenta de nuevo."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "No se pudo conectar al servidor."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def check_role(ctx):
    if REQUIRED_ROLE == '': return True
    role = discord.utils.get(ctx.author.roles, id=int(REQUIRED_ROLE))
    return role is not None

@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Game(name="!help para usar"))

@bot.command()
async def start(ctx):
    name = ctx.author.display_name
    text = (
        f"👋 Bienvenido, {name}!\n\n"
        "Soy el Bot de Free Fire Bio Updater.\n"
        "Úsame para actualizar tu bio de FF al instante.\n\n"
        "📌 Comandos:\n"
        " `!start` – Mostrar este mensaje\n"
        " `!help` – Como usar el bot\n"
        " `!bio` – Actualizar tu bio de FF\n"
        f"👤 Owner: {OWNER_USERNAME}"
    )
    await ctx.send(text)

@bot.command()
async def help(ctx):
    owner_line = f"\n\n👤 *Owner:* {OWNER_USERNAME}" if OWNER_USERNAME else ""
    text = (
        "📖 *Como Actualizar Tu Bio*\n\n"
        "Formato:\n"
        "`!bio <access_token> <nuevo texto de bio>`\n\n"
        "🔑 *Access Token* puede ser:\n"
        "• Token plano: `d8a4e0bd68fb8e13...`\n\n"
        "• Link Kiosgamer:\n"
        " `https://ticket.kiosgamer.co.id/?eat=TOKEN...`\n\n"
        "• Link Garena Help:\n"
        " `https://help.garena.com/?access_token=TOKEN...`\n\n"
        "📝 *Bio* puede tener texto, símbolos, emojis.\n\n"
        "Ejemplo:\n"
        "`!bio d8a4e0bd68fb FREE FIRE PRO ⚡`"
        f"{owner_line}"
    )
    await ctx.send(text)

@bot.command()
async def bio(ctx, token_raw: str = None, *, bio_text: str = None):
    try:
        if not await check_role(ctx):
            return await ctx.send(f"❌ No tienes el rol requerido para usar este comando.")

        if not token_raw or not bio_text:
            await ctx.send(
                "❌ Formato incorrecto!\n\n"
                "Usa: `!bio <access_token> <nueva bio>`\n"
                "Escribe `!help` para más info."
            )
            return

        token = extract_access_token(token_raw)
        if token is None:
            await ctx.send(
                "❌ Formato de token inválido!\n\n"
                "Formatos aceptados:\n"
                "• Token plano\n"
                "• Link de Kiosgamer\n"
                "• Link de Garena Help\n"
                "Escribe `!help` para ver ejemplos."
            )
            return

        if not bio_text:
            await ctx.send("❌ La bio no puede estar vacía!")
            return

        wait_msg = await ctx.send("⏳ Actualizando tu bio, espera...")

        result = call_bio_api(token, bio_text)
        await wait_msg.delete()

        if result.get('status') == 'success':
            nickname = result.get('nickname', 'Unknown')
            uid = result.get('uid', 'N/A')
            platform = result.get('platform', 'N/A')
            region = result.get('region', 'N/A')
            new_bio = result.get('bio', bio_text)

            embed = discord.Embed(title="✅ Bio actualizada!", color=0x00ff00)
            embed.add_field(name="👤 Player", value=f"`{nickname}`", inline=True)
            embed.add_field(name="🆔 UID", value=f"`{uid}`", inline=True)
            embed.add_field(name="📱 Platform", value=f"`{platform}`", inline=True)
            embed.add_field(name="🌍 Region", value=f"`{region}`", inline=True)
            embed.add_field(name="📝 Nueva Bio", value=new_bio, inline=False)
            embed.set_footer(text="👑 Credit: @itzpaglu")
            await ctx.send(embed=embed)

        else:
            error_msg = result.get('message', 'Error desconocido.')
            await ctx.send(f"❌ Falló al actualizar bio!\n\n🔴 Error: {error_msg}")

    except Exception as e:
        logger.error(f"Bio command error: {e}")
        await ctx.send("❌ Algo salió mal. Intenta más tarde.")

def run_bot():
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    # Correr bot y flask juntos
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
