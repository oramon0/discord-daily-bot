import os
import asyncio
import discord
from discord.ext import commands
from discord.sinks import WaveSink
from openai import OpenAI

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

client_ai = OpenAI(api_key=OPENAI_API_KEY)

# --- Função para transcrever com OpenAI ---
def transcrever_arquivo(path: str) -> str:
    with open(path, "rb") as f:
        r = client_ai.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f
        )
    return r.text

# --- Eventos ---
@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user}")

# --- Comandos básicos ---
@bot.command()
async def entrar(ctx):
    """Entra no canal de voz do autor"""
    if ctx.author.voice is None:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")
    if ctx.voice_client:
        return await ctx.send("Já estou em um canal.")
    await ctx.author.voice.channel.connect()
    await ctx.send("🎙️ Entrei no canal de voz.")

@bot.command()
async def sair(ctx):
    """Sai do canal de voz"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Saí do canal de voz.")
    else:
        await ctx.send("❌ Não estou em um canal.")

# --- Gravação controlada ---
@bot.command()
async def gravar(ctx):
    """Inicia gravação até usar !parar"""
    vc = ctx.voice_client
    if not vc:
        if ctx.author.voice is None:
            return await ctx.send("❌ Você precisa estar em um canal de voz.")
        vc = await ctx.author.voice.channel.connect()

    if vc.is_recording():
        return await ctx.send("⚠️ Já estou gravando.")

    sink = WaveSink()
    vc.start_recording(sink, finished_callback, ctx)
    await ctx.send("⏺️ Gravando... use !parar para finalizar.")

@bot.command()
async def parar(ctx):
    """Para a gravação e transcreve"""
    vc = ctx.voice_client
    if not vc or not vc.is_recording():
        return await ctx.send("❌ Não estou gravando.")
    vc.stop_recording()
    await ctx.send("🛑 Parando a gravação...")

# --- Gravação rápida (10s) ---
@bot.command(name="gravar10")
async def gravar10(ctx):
    """Grava 10 segundos e transcreve"""
    vc = ctx.voice_client
    if not vc:
        if ctx.author.voice is None:
            return await ctx.send("❌ Você precisa estar em um canal de voz.")
        vc = await ctx.author.voice.channel.connect()

    sink = WaveSink()
    vc.start_recording(sink, finished_callback, ctx)
    await ctx.send("⏺️ Gravando por 10 segundos...")
    await asyncio.sleep(10)
    vc.stop_recording()

# --- Callback para processar gravação ---
async def finished_callback(sink: WaveSink, ctx: commands.Context):
    await ctx.send("🔄 Processando áudio...")

    partes = []
    for user, audios in sink.audio_data.items():
        for audio in audios:
            caminho = audio.file
            try:
                texto = await asyncio.to_thread(transcrever_arquivo, caminho)
                partes.append(f"**{user.display_name}:** {texto}")
            except Exception as e:
                partes.append(f"**{user.display_name}:** [erro na transcrição: {e}]")
            try:
                os.remove(caminho)
            except:
                pass

    if partes:
        saida = "\n".join(partes)
        if len(saida) <= 1900:
            await ctx.send(f"📝 **Transcrição**\n{saida}")
        else:
            with open("transcricao.txt", "w", encoding="utf-8") as f:
                f.write(saida)
            await ctx.send("📝 **Transcrição (arquivo)**", file=discord.File("transcricao.txt"))
            os.remove("transcricao.txt")
    else:
        await ctx.send("⚠️ Não capturei áudio suficiente.")

bot.run(DISCORD_TOKEN)
