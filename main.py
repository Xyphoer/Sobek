from discord.ext import commands

import discord
import asyncio
import logging
import json
from asqlite import asqlite

intents = discord.Intents.all()

cogwheels = ['cogs.Utility', 'cogs.General']

bot = commands.Bot(command_prefix = '?', intents=intents, case_insensitive=True)


if __name__ == "__main__":
    for wheel in cogwheels:
        bot.load_extension(wheel)

@bot.event
async def on_ready():
    print(f'logged in as {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def reload(ctx):
    """Reloads the extentions."""
    m = await ctx.send('reloading...')
    for wheel in cogwheels:
        try:
            bot.reload_extension(wheel)
        except Exeption as e:
            await ctx.send(f'Error reloading {wheel}')
            print(e)
    await m.edit(content = 'reloaded')

@bot.command()
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    """Shuts down the bot.

    This can only be done by administrators."""
    embed=discord.Embed(title='Shutdown',
        description='Are you sure you want to shutdown Sobek?')
    embed.set_footer(text='This is not a restart. The bot will not reconnect until Nyx_2#8763 is available to connect it.')
    m = await ctx.send(embed=embed)
    await m.add_reaction('\N{WHITE HEAVY CHECK MARK}')
    await m.add_reaction('\N{CROSS MARK}')

    def check(reaction, user):
        return user == ctx.author and (str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}' or str(reaction.emoji) == '\N{CROSS MARK}')

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60, check=check)
    except asyncio.TimeoutError:
        await m.clear_reactions()
        timeout = discord.Embed(title='Timeout')
        await m.edit(embed=timeout)
    else:
        if str(reaction) == '\N{WHITE HEAVY CHECK MARK}':
            try:
                await m.clear_reactions()
            except discord.Forbidden:
                await ctx.send('Cannot clear reactions.')
            shutting_down = discord.Embed(title='Shutting Down')
            shutting_down.set_footer(text=f'Called by {ctx.author.name}  {ctx.author.id}.')
            await m.edit(embed=shutting_down)
            await bot.close()
        else:
            try:
                await m.clear_reactions()
            except discord.Forbidden:
                await ctx.send('Cannot clear reactions.')
            cancelled = discord.Embed(title='Cancelled')
            cancelled.set_footer(text=f'Called by {ctx.author.name}  {ctx.author.id}.')
            await m.edit(embed=cancelled)

async def data_storage():
    async with asqlite.connect('SobekStorage1.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS Memorial 
                (tracking INT PRIMARY KEY, WS1_DA, WS2_DA, WS1_H, WS2_H)''')
            await cursor.execute('''CREATE TABLE IF NOT EXISTS lastseen
                (member, seen)''')
            #await cursor.execute("INSERT OR REPLACE INTO Memorial(tracking) VALUES(1)")

asyncio.run(data_storage())

bot.run('TOKEN')