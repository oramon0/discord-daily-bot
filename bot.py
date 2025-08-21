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

# ---------- Transcrição (síncrona; rodamos em thread) ----------
def transcrever_arquivo(path: str) -> str:
    with open(path, "rb") as f:
        r = client_ai.audio.transcriptions.create(
            model="whisper-1",  # ou "gpt-4o-mini-transcribe" se preferir
            file=f
        )
    return r.text

# ---------- Eventos ----------
@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user}")

# ---------- Comandos util ----------
@bot.command()
async def entrar(ctx):
    """Entra no canal de voz do autor."""
    if ctx.author.voice is None:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")
    if ctx.voice_client:
        return await ctx.send("Já estou em um canal.")
    await ctx.author.voice.channel.connect()
    await ctx.send("🎙️ Entrei no canal de voz.")

@bot.command()
async def sair(ctx):
    """Sai do canal de voz atual."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Saí do canal de voz.")
    else:
        await ctx.send("❌ Não estou em um canal.")

# ---------- Gravação controlada ----------
@bot.command()
async def gravar(ctx):
    """Inicia a gravação até usar !parar."""
    vc = ctx.voice_client
    if not vc:
        if ctx.author.voice is None:
            return await ctx.send("❌ Você precisa estar em um canal de voz.")
        vc = await ctx.author.voice.channel.connect()

    try:
        if getattr(vc, "is_recording", lambda: False)():
            return await ctx.send("⚠️ Já estou gravando.")

        sink = WaveSink()

        # callback síncrono: agenda a corrotina no loop do bot
        def finished_callback(sink_obj, ctx_arg):
            asyncio.run_coroutine_threadsafe(
                processar_gravacao(ctx_arg, sink_obj),
                bot.loop
            )

        vc.start_recording(sink, finished_callback, ctx)
        await ctx.send("⏺️ Gravando... use **!parar** para finalizar.")
    except Exception as e:
        await ctx.send(f"⚠️ Erro ao iniciar gravação: {e}")

@bot.command()
async def parar(ctx):
    """Para a gravação e inicia a transcrição."""
    vc = ctx.voice_client
    if not vc or not getattr(vc, "is_recording", lambda: False)():
        return await ctx.send("❌ Não estou gravando.")
    vc.stop_recording()
    await ctx.send("🛑 Parando a gravação...")

# ---------- Gravação rápida de 10s ----------
@bot.command(name="gravar10")
async def gravar10(ctx):
    """Grava 10 segundos e transcreve."""
    vc = ctx.voice_client
    if not vc:
        if ctx.author.voice is None:
            return await ctx.send("❌ Você precisa estar em um canal de voz.")
        vc = await ctx.author.voice.channel.connect()

    sink = WaveSink()

    def finished_callback(sink_obj, ctx_arg):
        asyncio.run_coroutine_threadsafe(
            processar_gravacao(ctx_arg, sink_obj),
            bot.loop
        )

    vc.start_recording(sink, finished_callback, ctx)
    await ctx.send("⏺️ Gravando por **10s**...")
    await asyncio.sleep(10)
    vc.stop_recording()

# ---------- Processa a gravação (transcreve e envia) ----------
async def processar_gravacao(ctx: commands.Context, sink: WaveSink):
    await ctx.send("🔄 Processando áudio...")

    partes = []
    # sink.audio_data: dict {Member -> AudioData}
    for user, audio in sink.audio_data.items():
        caminho = audio.file  # arquivo WAV temporário
        try:
            texto = await asyncio.to_thread(transcrever_arquivo, caminho)
            partes.append(f"**{getattr(user, 'display_name', str(user))}:** {texto}")
        except Exception as e:
            partes.append(f"**{getattr(user, 'display_name', str(user))}:** [erro na transcrição: {e}]")
        finally:
            try:
                os.remove(caminho)
            except Exception:
                pass

    if partes:
        saida = "\n".join(partes)
        if len(saida) <= 1900:
            await ctx.send(f"📝 **Transcrição**\n{saida}")
        else:
            with open("transcricao.txt", "w", encoding="utf-8") as f:
                f.write(saida)
            await ctx.send("📝 **Transcrição (arquivo)**", file=discord.File("transcricao.txt"))
            try:
                os.remove("transcricao.txt")
            except Exception:
                pass
    else:
        await ctx.send("⚠️ Não capturei áudio suficiente.")

bot.run(DISCORD_TOKEN)
