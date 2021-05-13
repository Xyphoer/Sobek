import discord
from discord.ext import commands
import asyncio
import json
from asqlite import asqlite
import re
from .utils import checks
from .utils.formats import time_converter

class General(commands.Cog):
    """General commands for use by pretty much anyone."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def remind(self, ctx, duration, *, content):
        """Reminds you of something a specified duration later.

        When using multiple styles of time, either write them without spaces, or wrap them in quotes.
        This is so there doesn't have to be a mandatory deliminator.

        format:
            ?remind 2d5h3m some reminder here.
            ?remind 5.8h1d some reminder here.
            ?remind "1d 2h 3m" some reminder here."""
        value = time_converter(duration)
        if not value:
            await ctx.send('Invalid time: make sure to format each amount of time with the appropriate letter.')
            return

        if value['total time'] // 86400 > 10:
            await ctx.send('Max of ten days.')
            return

        await ctx.send(f'Reminder set for {value["days"]}d {value["hours"]}h {value["minutes"]}m.')
        await asyncio.sleep(value['total time'])
        await ctx.send(f'{ctx.author.mention} {value["days"]}d {value["hours"]}h {value["minutes"]}m ago:\n{content}\n{ctx.message.jump_url}')

    @commands.command(aliases=['nick'])
    async def nickname(self, ctx, *, nickname):
        """Changes your nickname to whatever follows the command.

        Usage: ?nick new nickname"""
        old = ctx.author.display_name
        await ctx.author.edit(nick=nickname)
        await ctx.send(f'Successfully change nickname from {old} to {nickname}')

    @commands.command(aliases=['RS1','RS2','RS3','RS4','RS5','RS6','RS7','RS8','RS9','RS10','RS11'])
    @checks.blocked_channels('lobby', 'mess-hall')
    async def RS(self, ctx):
        """Adds or removes the specified RS roles.

        Usage: ?RS4"""
        role = discord.utils.get(ctx.guild.roles, name=f'RS{ctx.message.content[3:]}')
        if role != None:
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
                await ctx.send(f"RS{ctx.message.content[3:]} removed.")
            else:
                await ctx.author.add_roles(role)
                await ctx.send(f"RS{ctx.message.content[3:]} added.")
        else:
            await ctx.send(f'Role RS{ctx.message.content[3:]} not found.')

def setup(bot):
    bot.add_cog(General(bot))
