import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, ButtonStyle
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
import os
import json
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
# Discord bot setup


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load environment variables from .env file
load_dotenv()

# Secret token variable (replace 'YOUR_BOT_TOKEN' with your actual bot token)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Flask setup
app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


# Load data from JSON files or create if they don't exist
if not os.path.exists('quotes.json'):
    with open('quotes.json', 'w') as f:
        json.dump([], f)

if not os.path.exists('polls.json'):
    with open('polls.json', 'w') as f:
        json.dump({}, f)

if not os.path.exists('commands.json'):
    with open('commands.json', 'w') as f:
        json.dump({}, f)

# Load JSON data
def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Quotes commands
@bot.command()
async def addquote(ctx, *, quote: str):
    quotes = load_data('quotes.json')
    quotes.append(quote)
    save_data('quotes.json', quotes)
    await ctx.send(f'Quote added by {ctx.author.mention}!')

@bot.command()
async def quote(ctx, quote_id: int = None):
    quotes = load_data('quotes.json')
    if quote_id is None:
        quote = random.choice(quotes)
    elif 0 <= quote_id < len(quotes):
        quote = quotes[quote_id]
    else:
        await ctx.send(f'Quote ID out of range, {ctx.author.mention}!')
        return
    await ctx.send(f'{quote} (requested by {ctx.author.mention})')

@bot.command()
async def quoteoftheday(ctx):
    quotes = load_data('quotes.json')
    quote = random.choice(quotes)
    await ctx.send(f'Quote of the Day: {quote} (requested by {ctx.author.mention})')

@bot.command()
async def listquotes(ctx):
    quotes = load_data('quotes.json')
    if not quotes:
        await ctx.send(f'There are no quotes stored, {ctx.author.mention}.')
        return
    formatted_quotes = '\n'.join([f'{idx}: {quote}' for idx, quote in enumerate(quotes)])
    await ctx.send(f'List of quotes (requested by {ctx.author.mention}):\n{formatted_quotes}')

# Poll commands
# Storage for polls
polls = {}
poll_counter = 0

class Poll:
    def __init__(self, question, options):
        self.question = question
        self.options = options
        self.votes = [0] * len(options)
        self.voters = []

class PollButton(Button):
    def __init__(self, label, poll_id, option_index):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.poll_id = poll_id
        self.option_index = option_index

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        poll = polls[self.poll_id]

        if user_id in poll.voters:
            await interaction.response.send_message("You have already voted!", ephemeral=True)
        else:
            poll.votes[self.option_index] += 1
            poll.voters.append(user_id)
            await interaction.response.send_message(f"Voted for: {self.label}", ephemeral=True)

class PollView(View):
    def __init__(self, poll_id):
        super().__init__(timeout=None)
        poll = polls[poll_id]
        for i, option in enumerate(poll.options):
            self.add_item(PollButton(label=option, poll_id=poll_id, option_index=i))

@bot.command()
async def poll(ctx, *, question_and_options: str):
    global poll_counter
    global polls

    try:
        question, options = question_and_options.split(":", 1)
        options = [opt.strip() for opt in options.split(",")]
    except ValueError:
        await ctx.send("Invalid format. Use `!poll \"<question>\": <option1>, <option2>, <option3>, ...`")
        return

    poll_counter += 1
    poll_id = poll_counter
    polls[poll_id] = Poll(question, options)

    view = PollView(poll_id)
    embed = discord.Embed(title=f"Poll #{poll_id}", description=question, color=discord.Color.blue())
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)

    await ctx.send(embed=embed, view=view)

@bot.command()
async def pollresults(ctx, poll_id: int):
    global polls

    if poll_id not in polls:
        await ctx.send(f"No poll found with ID {poll_id}.")
        return

    poll = polls[poll_id]
    results = [f"{option}: {votes} votes" for option, votes in zip(poll.options, poll.votes)]
    description = "\n".join(results)

    embed = discord.Embed(title=f"Poll #{poll_id} Results", description=description, color=discord.Color.green())
    await ctx.send(embed=embed)

'''
@bot.command()
async def poll(ctx, question: str, *, options: str):
    options_list = [opt.strip() for opt in options.split(',')]
    if len(options_list) < 2:
        await ctx.send(f'A poll must have at least two options, {ctx.author.mention}.')
        return

    polls = load_data('polls.json')
    poll_id = len(polls)
    polls[poll_id] = {'question': question, 'options': options_list, 'votes': [0] * len(options_list)}
    save_data('polls.json', polls)

    # Create the embed for the poll
    embed = discord.Embed(title="New Poll", description=question, color=discord.Color.blue())
    for i, option in enumerate(options_list):
        embed.add_field(name=f"Option {i}", value=option, inline=False)
    embed.set_footer(text=f"Poll ID: {poll_id}")

    # Send the embed message
    message = await ctx.send(embed=embed)

    # Add reactions for voting
    reactions = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
    for i in range(len(options_list)):
        await message.add_reaction(reactions[i])

    await ctx.send(f'Poll created by {ctx.author.mention}!')

@bot.command()
async def pollresults(ctx, poll_id: int):
    polls = load_data('polls.json')
    if poll_id not in polls:
        await ctx.send(f'Invalid poll ID, {ctx.author.mention}!')
        return
    poll = polls[poll_id]
    results = '\n'.join(f'{opt}: {votes}' for opt, votes in zip(poll['options'], poll['votes']))
    await ctx.send(f'Poll results for "{poll["question"]}" (requested by {ctx.author.mention}):\n{results}')
'''
# List Polls From Json Command
@bot.command()
async def listpolls(ctx):
    polls = load_data('polls.json')
    if not polls:
        await ctx.send(f'No polls available, {ctx.author.mention}.')
        return
    formatted_polls = '\n'.join([f'ID {poll_id}: {poll["question"]}' for poll_id, poll in polls.items()])
    await ctx.send(f'List of polls (requested by {ctx.author.mention}):\n{formatted_polls}')

# Custom commands
@bot.command()
async def addcommand(ctx, command_name: str, *, response: str):
    custom_commands = load_data('commands.json')
    if command_name in custom_commands:
        await ctx.send(f'Command already exists, {ctx.author.mention}!')
        return
    custom_commands[command_name] = response
    save_data('commands.json', custom_commands)
    await ctx.send(f'Custom command {command_name} added by {ctx.author.mention}!')

@bot.command()
async def listcommands(ctx):
    custom_commands = load_data('commands.json')
    if not custom_commands:
        await ctx.send(f'No custom commands available, {ctx.author.mention}.')
        return
    await ctx.send(f'Available commands (requested by {ctx.author.mention}): {", ".join(custom_commands.keys())}')

# Command to explain input formats
@bot.command()
async def helpcommands(ctx):
    help_message = (
        "**Quotes Commands:**\n"
        "`!addquote <quote>` - Adds a quote.\n"
        "`!quote [quote_id]` - Retrieves a quote. If `quote_id` is not provided, a random quote is retrieved.\n"
        "`!quoteoftheday` - Retrieves a random quote as the quote of the day.\n"
        "`!listquotes` - Lists all quotes.\n\n"
        "**Poll Commands:**\n"
        "`!poll \"<question>\": <option1>, <option2>, <option3>, ...` - Creates a new poll with the specified question and options.\n"
        "`!pollresults <poll_id>` - Retrieves the results of a poll by its ID.\n"
        "`!listpolls` - Lists all polls with their IDs and questions.\n\n"
        "**Custom Commands:**\n"
        "`!addcommand <command_name> <response>` - Adds a custom command with the specified response.\n"
        "`!listcommands` - Lists all custom commands.\n\n"
        "**Utility Commands:**\n"
        "`!ping` - Checks if the bot is responsive.\n\n"
        "**Audio Commands:**\n"
        "`!join` - Bot joins the voice channel.\n"
        "`!play <url>` - Plays audio from the provided YouTube URL.\n"
        "`!queue_list` - Lists all the songs in the queue.\n"
        "`!skip` - Skips the currently playing song.\n"
        "`!pause` - Pauses the currently playing song.\n"
        "`!resume` - Resumes the paused song.\n"
        "`!leave` - Bot leaves the voice channel.\n"
    )
    await ctx.send(f'Command Help (requested by {ctx.author.mention}):\n{help_message}')

# Execute custom commands
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    custom_commands = load_data('commands.json')
    if message.content in custom_commands:
        await message.channel.send(custom_commands[message.content])
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {ctx.author.mention}')

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    message = reaction.message
    if not message.embeds:
        return

    embed = message.embeds[0]
    if not embed.footer.text.startswith("Poll ID:"):
        return

    poll_id = int(embed.footer.text.split(":")[1].strip())
    polls = load_data('polls.json')
    if poll_id not in polls:
        return

    reactions = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
    if reaction.emoji in reactions:
        option_index = reactions.index(reaction.emoji)
        if option_index < len(polls[poll_id]['options']):
            polls[poll_id]['votes'][option_index] += 1
            save_data('polls.json', polls)



####AUDIO SECTION###
if not discord.opus.is_loaded():
    discord.opus.load_opus('libopus.so')  # On Linux

queue = []
now_playing = None
voice_client = None

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn',
    'executable': 'ffmpeg'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except youtube_dl.utils.DownloadError as e:
            print(f"Error downloading: {e}")
            return None

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

async def play_next(ctx):
    global voice_client
    global now_playing

    if len(queue) == 0:
        now_playing = None
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
        return

    now_playing = queue.pop(0)
    player = await YTDLSource.from_url(now_playing, loop=bot.loop, stream=True)
    if player is None:
        await ctx.send(f'Error playing: {now_playing}')
        await play_next(ctx)
        return

    voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

    embed = discord.Embed(title="Now Playing", description=player.title, color=discord.Color.green())
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    view = View()
    view.add_item(Button(label="⏮️", style=ButtonStyle.primary, custom_id="previous"))
    view.add_item(Button(label="⏸️", style=ButtonStyle.primary, custom_id="pause"))
    view.add_item(Button(label="⏭️", style=ButtonStyle.primary, custom_id="next"))

    await ctx.send(embed=embed, view=view)

@bot.command()
async def join(ctx):
    global voice_client
    if ctx.author.voice is None:
        await ctx.send(f'{ctx.author.mention}, you are not connected to a voice channel.')
        return

    channel = ctx.author.voice.channel
    voice_client = await channel.connect()

@bot.command()
async def play(ctx, url):
    global voice_client

    if ctx.author.voice is None:
        await ctx.send(f'{ctx.author.mention}, you are not connected to a voice channel.')
        return

    channel = ctx.author.voice.channel

    if voice_client is None or not voice_client.is_connected():
        voice_client = await channel.connect()

    if not url.startswith("https://www.youtube.com/watch?v="):
        await ctx.send(f'{ctx.author.mention}, please provide a valid YouTube URL.')
        return

    queue.append(url)
    if now_playing is None:
        await play_next(ctx)
    else:
        await ctx.send(f'Added to queue by {ctx.author.mention}')

@bot.command()
async def queue_list(ctx):
    if len(queue) == 0:
        await ctx.send(f'The queue is empty, {ctx.author.mention}.')
        return

    description = '\n'.join([f"{i+1}. {url}" for i, url in enumerate(queue)])
    embed = discord.Embed(title="Queue", description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command()
async def skip(ctx):
    global voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()

@bot.command()
async def pause(ctx):
    global voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()

@bot.command()
async def resume(ctx):
    global voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

@bot.event
async def on_interaction(interaction: discord.Interaction):
    global voice_client
    custom_id = interaction.data["custom_id"]

    if custom_id == "previous":
        pass  # Add functionality for the previous button if needed
    elif custom_id == "pause":
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Paused", ephemeral=True)
        elif voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Resumed", ephemeral=True)
    elif custom_id == "next":
        if voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped", ephemeral=True)


'''
@bot.event
async def on_reaction_add(reaction, user):
    global voice_client
    if user == bot.user:
        return

    if reaction.message.embeds and reaction.message.embeds[0].title == "Now Playing":
        if str(reaction.emoji) == "⏸️":
            if voice_client.is_playing():
                voice_client.pause()
        elif str(reaction.emoji) == "⏭️":
            if voice_client.is_playing():
                voice_client.stop()
'''
# Run the bot
keep_alive()
bot.run(TOKEN)
