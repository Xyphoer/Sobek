import discord
from discord.ext import commands
import asyncio
import json
from asqlite import asqlite
import re

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
        regex_type = re.compile(r'd|h|m')
        regex_amount = re.compile(r'(\d+\.?\d*)|(\.\d+)')
        style = regex_type.findall(duration.lower())
        time_full = regex_amount.findall(duration.lower())
        time = []
        for y in time_full:
            for x in y:
                if x != '':
                    time.append(x)
        days, hours, minutes = (0, 0, 0)
        if len(style) < len(time):
            await ctx.send('Invalid time: make sure to format each amount of time with the appropriate letter.')
            return
        for amount in time.copy():
            if style[time.index(amount)] == 'd' and days == 0:
                days = float(amount)
                time.remove(amount)
                style.remove('d')
            elif style[time.index(amount)] == 'h' and hours == 0:
                hours = float(amount)
                time.remove(amount)
                style.remove('h')
            elif style[time.index(amount)] == 'm' and minutes == 0:
                minutes = float(amount)
                time.remove(amount)
                style.remove('m')
        total_time = days * 86400 + hours * 3600 + minutes * 60
        if total_time // 86400 > 10:
            await ctx.send('Max of ten days.')
            return
        await ctx.send(f'Reminder set for {days}d {hours}h {minutes}m.')
        await asyncio.sleep(total_time)
        await ctx.send(f'{ctx.author.mention} {days}d {hours}h {minutes}m ago:\n{content}\n{ctx.message.jump_url}')

    @commands.command(aliases=['nick'])
    async def nickname(self, ctx, *, nickname):
        """Changes your nickname to whatever follows the command.

        Usage: ?nick new nickname"""
        old = ctx.author.display_name
        await ctx.author.edit(nick=nickname)
        await ctx.send(f'Successfully change nickname from {old} to {nickname}')

    @commands.command(aliases=['RS1','RS2','RS3','RS4','RS5','RS6','RS7','RS8','RS9','RS10','RS11'])
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