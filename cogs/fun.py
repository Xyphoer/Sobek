import discord
from discord.ext import commands
import random
from .utils import checks
import asyncio

class Fun(commands.Cog):
    """Fun commands, generally for enjoyment."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['profile_picture', 'pic',])
    async def avatar(self, ctx, member: discord.Member = None):
        """
        Displays a members profile picture. Chooses a random member if none are specified.

        Usage:
        `?avatar`
        `?avatar 341331627839848448`
        """
        if not member:
            member = random.choice(ctx.guild.members)
            embed = discord.Embed(description = f'||{member.mention}||')
        else:
            embed = discord.Embed(description = f'{member.mention}')

        embed.set_image(url = member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['colour'])
    @checks.is_dragon()
    async def color(self, ctx, code = None):
        """
        Assigns or updates a personal, 24 hour, color role with the provided color or a random color.

        Can remove your color role by specifying 'remove' as the code.

        Usage:
        `?color`
        `?color 12648430`
        `?colour 0xc0ffee`
        `?color c0ffee`
        `?color remove`
        """
        if code == 'remove':
            for role in ctx.member.roles:
                if role.name == 'color':
                    ctx.member.remove_roles(role, reason = 'color role removal')
                    await ctx.send('Removed color role.')
                    return
            else:
                await ctx.send('No color role to remove.')
                return

        if code:
            try:
                code = int(code)
                if code > 16777215:
                    await ctx.send('Color value must be 16777215 or less.')
                    return
                assign_color = code
            except ValueError:
                try:
                    if code[:2] == '0x':
                        assign_color = int(code, 0)
                    else:
                        assign_color = int(code, 16)
                except ValueError:
                    await ctx.send('Color code must be an integer or hex value.')
                    return

        else:
            assign_color = discord.Colour.random()

        if 'color' not in [role.name for role in ctx.author.roles]:
            color_role = []
            for role in ctx.guild.roles[::-1]:
                if role.name == 'color':
                    color_role.append(role)
                    if role.members == []:
                        color_role = role
                        break
            else:
                color_role = random.choice(color_role)
                for member in color_role.members:
                    member.remove_roles(color_role, reason = 'Swapping member')

            await ctx.author.add_roles(role, reason = 'color assignment')
            await role.edit(color = assign_color)
            await ctx.send(f'Assigned color with hex code: {hex(color_role.color.value)} int code: {color_role.color.value}')

        else:
            color_role = [role for role in ctx.author.roles if role.name == 'color'][0]
            await color_role.edit(color = assign_color)
            await ctx.send(f'Changed color role to hex code: {hex(color_role.color.value)} int code: {color_role.color.value}')

def setup(bot):
    bot.add_cog(Fun(bot))