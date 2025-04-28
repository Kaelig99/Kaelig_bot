import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp as youtube_dl

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.voice_states = True

bot = commands.Bot(command_prefix=".", intents=intents)
queue = []

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="général")
    if channel:
        await channel.send(f"Bienvenue sur le serveur, {member.mention} !")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

@bot.command()
async def role(ctx, role_name: str, *, custom_message: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    message = await ctx.send(custom_message)
    await message.add_reaction("\u2705")
    await message.add_reaction("\u274c")
    bot.role_message_id = message.id
    bot.assigned_role_name = role_name

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != getattr(bot, "role_message_id", None):
        return
    if str(payload.emoji) not in ["\u2705", "\u274c"]:
        return
    guild = bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    for reaction in message.reactions:
        users = await reaction.users().flatten()
        if payload.member in users and str(reaction.emoji) != str(payload.emoji):
            await message.remove_reaction(reaction.emoji, payload.member)
    member = guild.get_member(payload.user_id)
    role_name = getattr(bot, "assigned_role_name", "Membre")
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = await guild.create_role(name=role_name)
    if str(payload.emoji) == "\u2705":
        await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != getattr(bot, "role_message_id", None):
        return
    if str(payload.emoji) != "\u2705":
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role_name = getattr(bot, "assigned_role_name", "Membre")
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await member.remove_roles(role)

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("Tu dois être connecté à un salon vocal !")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("Je ne suis connecté à aucun salon vocal !")

@bot.command()
async def play(ctx, url):
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    queue.append(url)
    await ctx.send(f"Ajouté à la file d'attente: {url}")
    if not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    if queue:
        url = queue.pop(0)
        ydl_opts = {'format': 'bestaudio'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            ctx.voice_client.play(discord.FFmpegPCMAudio(url2), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"Lecture en cours: {url}")

@bot.command()
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Musique passée !")

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Musique en pause !")

@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Musique relancée !")

@bot.command()
async def queue_list(ctx):
    if queue:
        await ctx.send("File d'attente:\n" + "\n".join(queue))
    else:
        await ctx.send("La file d'attente est vide !")

@bot.command()
async def stop(ctx):
    global queue
    queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("La musique est arrêtée et le bot a quitté le salon.")

@bot.command(name="commands")
async def commands_list(ctx):
    help_message = (
        "**Commandes disponibles :**\n"
        ".role <nom_du_role> <message> : Crée un message avec réactions pour assigner un rôle\n"
        ".join : Le bot rejoint votre salon vocal\n"
        ".leave : Le bot quitte le salon vocal\n"
        ".play <url YouTube> : Joue une musique depuis YouTube\n"
        ".pause : Met la musique en pause\n"
        ".resume : Reprend la musique\n"
        ".skip : Passe à la musique suivante\n"
        ".queue_list : Affiche la file d'attente de musiques\n"
        ".stop : Arrête la musique et vide la file d'attente\n"
    )
    await ctx.send(help_message)

bot.run(os.getenv('TOKEN'))
