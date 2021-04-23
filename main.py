from discord.ext import commands

import discord
import asyncio
import logging
import json
from asqlite import asqlite


class MyHelpCommand(commands.HelpCommand):

    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title='Help Menu', color=11761390)
        embed.set_footer(text = 'Type ?help command for more info on a command.\nYou can also type ?help category for more info on a category.')

        for cog in mapping:
            commands = f"{cog.description if cog else ''}\n\n" + '\n'.join(['-' + command.name for command in await self.filter_commands(mapping[cog], sort=True)])
            name = f'__**{cog.qualified_name if cog else cog}:**__'
            embed.add_field(name = name, value = commands)

        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):

        description = []

        for command in await self.filter_commands(cog.get_commands(), sort=True):
            description.append(f'\n\n__**{command.qualified_name}**__: {command.short_doc}')

        embed = discord.Embed(title=f'{cog.qualified_name}',
            description = cog.description + ''.join(description),
            color=11761390)
        embed.set_footer(text = 'Type ?help command for more info on a command.\nYou can also type ?help category for more info on a category.')

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title = f'{command.name} - {" | ".join(command.aliases)}',
            description = f'{self.get_command_signature(command)}\n\n{command.help}',
            color = 11761390)
        embed.set_footer(text = 'Type ?help command for more info on a command.\nYou can also type ?help category for more info on a category.')

        await self.context.send(embed=embed)


intents = discord.Intents.all()

cogwheels = ('Utility', 'General')

bot = commands.Bot(command_prefix = '`', intents=intents, case_insensitive=True, help_command=MyHelpCommand())


if __name__ == "__main__":
    for wheel in cogwheels:
        bot.load_extension(f'cogs.{wheel}')

@bot.event
async def on_ready():
    print(f'logged in as {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, *wheels):
    """Reloads a specified extention, or all extentions."""
    if not wheels: wheels = cogwheels
    m = await ctx.send('reloading...')
    for wheel in cogwheels:
        try:
            bot.reload_extension(f'cogs.{wheel}')
        except Exeption as e:
            await ctx.send(f'Error reloading {wheel}:\n{e}')
    await m.edit(content = f'reloaded {", ".join(wheels)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    """Shuts down the bot."""
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

async def on_command_error(ctx, error):
    await ctx.send(error)

async def data_storage():
    async with asqlite.connect('SobekStorage1.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS lastseen
                (member, seen, ws, status)''')
            ##await cursor.execute("ALTER TABLE lastseen ADD COLUMN status text")
            ##await cursor.execute("DROP TABLE Memorial")
            #await cursor.execute("ALTER TABLE lastseen ADD COLUMN ws text")
            #await cursor.execute("INSERT OR REPLACE INTO Memorial(tracking) VALUES(1)")

asyncio.run(data_storage())

with open('token.txt') as token_file:
    TOKEN = token_file.read()

bot.run(TOKEN)
