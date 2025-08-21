import os
import asyncio
import discord
from discord.ext import commands
from openai import OpenAI

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
client_ai = OpenAI(api_key=OPENAI_API_KEY)

async def transcrever_arquivo(path: str) -> str:
    with open(path, "rb") as f:
        r = client_ai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return r.text

@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def entrar(ctx):
    if ctx.author.voice is None:
        return await ctx.send("Entre em um canal de voz primeiro.")
    if ctx.voice_client is not None:
        return await ctx.send("Já estou em um canal de voz.")
    await ctx.author.voice.channel.connect()
    await ctx.send("🎙️ Entrei no canal de voz.")

@bot.command()
async def sair(ctx):
    if ctx.voice_client is None:
        return await ctx.send("Não estou em um canal de voz.")
    await ctx.voice_client.disconnect()
    await ctx.send("👋 Saí do canal de voz.")

@bot.command()
async def gravar(ctx, segundos: int = 60):
    vc: discord.VoiceClient = ctx.voice_client
    if vc is None:
        return await ctx.send("Eu preciso estar em um canal de voz. Use !entrar.")

    await ctx.send(f"⏺️ Gravando por {segundos}s...")

    sink = discord.sinks.WaveSink()  # grava cada usuário em wav
    recordings = await discord.sinks.record(vc, sink, timeout=segundos)

    await ctx.send("🛑 Gravação finalizada. Transcrevendo...")

    partes = []
    for user, files in recordings.items():
        for a in files:
            caminho = a.file
            try:
                texto = await asyncio.to_thread(transcrever_arquivo, caminho)
                partes.append(f"**{user.display_name}:** {texto}")
            except Exception as e:
                partes.append(f"**{user.display_name}:** [erro: {e}]")

    if not partes:
        return await ctx.send("Não capturei áudio suficiente.")

    saida = "\n".join(partes)
    if len(saida) < 1800:
        await ctx.send(f"📝 **Transcrição da daily**\n{saida}")
    else:
        with open("transcricao.txt", "w", encoding="utf-8") as f:
            f.write(saida)
        await ctx.send("📝 **Transcrição da daily (arquivo)**", file=discord.File("transcricao.txt"))

bot.run(DISCORD_TOKEN)
