import discord
from discord.ext import commands
import random
import checks
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
    async def color(self, ctx, int_code: int = None):
        """
        Assigns or updates a personal, 24 hour, color role with the provided color or a random color.

        Usage:
        `?color`
        `?color 12648430`
        """
        assign_color = int_code if int_code else discord.Colour.random()

        if 'color' not in [role.name for role in ctx.author.roles]:
            color_role = ctx.guild.create_role(reason = 'color assignment for' + ctx.author.name, name = 'color', color = assign_color)
            await color_role.edit(position = self.top_role.position - 2)
            await ctx.author.add_roles(color_role, reason = 'color assignment')
            await ctx.send(f'Assigned color role with hex code: {hex(color_role.color.value)} int code: {color_role.color.value}')
            await asyncio.sleep(86400)
            color_role.delete(reason = 'color role time up.')
        else:
            color_role = [role for role in ctx.author.roles if role.name == 'color'][0]
            await color_role.edit(color = assign_color)
            await ctx.send(f'Changed color role to hex code: {hex(color_role.color.value)} int code: {color_role.color.value}')