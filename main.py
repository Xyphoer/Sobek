from discord.ext import commands

import discord
import asyncio
import logging
import json
import traceback
import sys
from asqlite import asqlite
from cogs.utils.formats import compare_containers


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

cogwheels = ('utility', 'general', 'mod', 'fun')

bot = commands.Bot(command_prefix = '`', intents=intents, case_insensitive=True, help_command=MyHelpCommand())


if __name__ == "__main__":
    for wheel in cogwheels:
        bot.load_extension(f'cogs.{wheel}')

@bot.event
async def on_ready():
    print(f'logged in as {bot.user.name}')

@bot.command(hidden = True)
@commands.is_owner()
async def reload(ctx, *wheels):
    """Reloads a specified extention, or all extentions."""
    if not wheels: wheels = cogwheels
    wheels = compare_containers(wheels, cogwheels)
    if not wheels:
        await ctx.send(f'Failed to find cog(s) {", ".join(wheels)}.')
    m = await ctx.send('reloading...')
    for wheel in wheels:
        try:
            bot.reload_extension(f'cogs.{wheel}')
        except Exception as e:
            await ctx.send(f'Error reloading {wheel}')
            traceback.print_exc()
    await m.edit(content = f'reloaded {", ".join(wheels)}')

@bot.command(hidden = True)
@commands.is_owner()
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
            for role in ctx.guild.roles:
                if role.name == 'color':
                    await role.delete(reason = 'shutting down, color role purge.')
            await m.clear_reactions()
            shutting_down = discord.Embed(title='Shutting Down')
            shutting_down.set_footer(text=f'Called by {ctx.author.name}  {ctx.author.id}.')
            await m.edit(embed=shutting_down)
            await bot.close()
        else:
            await m.clear_reactions()
            cancelled = discord.Embed(title='Cancelled')
            cancelled.set_footer(text=f'Called by {ctx.author.name}  {ctx.author.id}.')
            await m.edit(embed=cancelled)

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, discord.Forbidden):
            await ctx.send('I have insufficient permissions to perform this task.')
            return

    if isinstance(error, commands.NotOwner) or isinstance(error, commands.MissingPermissions):
        await ctx.send('You are not permitted to use this command.')
    elif isinstance(error, commands.MissingRole):
        await ctx.send(f'You must have the {error.missing_role} role to use this command.')
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f'I require the following additional permissions for this command: {error.missing_perms}')
    elif isinstance(error, commands.BotMissingRole):
        await ctx.send(f'I require the {error.missing_role} role for this command.')
    elif isinstance(error, commands.CheckFailure):
        await ctx.send('The requirements for you to use this command have not been met.')

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'`{str(error.param).split(":")[0]}` is a required specification.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send(error)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(error)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def data_storage():
    async with asqlite.connect('SobekStorage1.db') as conn:
        async with conn.cursor() as cursor:
            ##await cursor.execute('''DROP TABLE lastseen''')
            await cursor.execute('''CREATE TABLE IF NOT EXISTS lastseen
                (member, seen, ws, status)''')
            ##await cursor.execute("ALTER TABLE lastseen ADD COLUMN status text")
            ##for member in bot.get_guild(443747736555225102).get_role(444548579839705089).members:
                ##await cursor.execute('UPDATE lastseen SET status = ? WHERE member = ?', (member.raw_status, member.id))
            ##await cursor.execute("DROP TABLE Memorial")
            #await cursor.execute("ALTER TABLE lastseen ADD COLUMN ws text")

asyncio.run(data_storage())

with open('token.txt') as token_file:
    TOKEN = token_file.read()

bot.run(TOKEN)