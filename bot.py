import discord
from discord.ext import commands
from discord.sinks import WaveSink
import asyncio
import os
import openai

# Configurações
TOKEN = os.getenv("DISCORD_TOKEN")   # seu token do bot
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user}")

@bot.command()
async def gravar(ctx, segundos: int = 10):
    if ctx.author.voice is None:
        await ctx.send("❌ Você precisa estar em um canal de voz.")
        return

    vc = await ctx.author.voice.channel.connect()
    sink = WaveSink()

    async def finished_callback(sink, *args):
        text_final = ""
        for user_id, audio in sink.audio_data.items():
            filename = f"record_{user_id}.wav"
            with open(filename, "wb") as f:
                f.write(audio.file.getbuffer())

            # --- Transcrevendo com Whisper ---
            try:
                with open(filename, "rb") as audio_file:
                    transcript = openai.audio.transcriptions.create(
                        model="gpt-4o-mini-transcribe",
                        file=audio_file
                    )
                text_final += f"🗣 <@{user_id}>: {transcript.text}\n"
            except Exception as e:
                text_final += f"⚠️ Erro ao transcrever áudio de <@{user_id}>: {e}\n"

            # remove arquivo depois de usar
            os.remove(filename)

        if text_final.strip() == "":
            text_final = "⚠️ Não consegui transcrever nada."
        await ctx.send(text_final)

        # desconectar no final
        await vc.disconnect()

    vc.start_recording(
        sink,
        finished_callback,
        ctx.channel
    )

    await ctx.send(f"🎙 Gravando por {segundos}s...")
    await asyncio.sleep(segundos)
    vc.stop_recording()

bot.run(TOKEN)
