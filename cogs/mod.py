import discord
from discord.ext import commands
from .utils import checks
from typing import Optional

class Mod(commands.Cog):
    """Moderation commands exclusive to Officers and Admins"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.is_officer()
    async def kick(self, ctx, members: commands.Greedy[discord.Member] = [], *, reason = None):
        """
        Kicks the specified member(s) for the optional reason.

        Members can be specified by mention, name, or id.
        Reason can be any text.

        Usage:
        `?kick Nyx_2#8763 beligerent`
        `?kick my_id_here Complete disregard for human decency`
        `?kick my_id_here Xyphoer_id_here just because`
        `?kick Nyx_2`
        """
        total = []
        for member in members:
            await member.kick(reason = reason)
            total.append(f'{member.name}({member.id})')
        if total: await ctx.send(f'Kicked {", ".join(total)} with reason: {reason}')
        else: await ctx.send('Specify a member to kick.')

    @commands.command()
    @checks.is_officer()
    async def ban(self, ctx, members: commands.Greedy[discord.Member] = [], purge_days: int = 0, *, reason = None):
        """
        Bans the specified member(s) for the optional reason, purging messages from the amount of days specified (max 7).

        Members can be specified by mention, name, or id.
        Purge_days can be an integer of 0 - 7.
        Reason can be any text.

        Usage:
        `?ban Nyx_2#8763 I can't even remember why.`
        `?ban my_id_here 2 Failure to please.`
        `?ban my_id_here Xyphoer_id_here 1 In cahoots for global domination.`
        `?ban Nyx_2`
        """
        total = []
        for member in members:
            await member.ban(reason = reason, delete_message_days = purge_days if purge_days <= 7 else 7)
            total.append(f'{member.name}({member.id})')
        if total: await ctx.send(f'Banned {", ".join(total)}. Purged {purge_days if purge_days <= 7 else 7} days of messages. Reason: {reason}')
        else: await ctx.send('Specify a member to ban.')

    @commands.command()
    @checks.is_officer()
    async def purge(self, ctx, members: commands.Greedy[discord.Member] = [], role: Optional[discord.Role] = None, *, reason = None):
        """
        Purges all roles from specified members. Optionally add's a role as well. (Useful for converting members to friends)

        Members can be specified by mention, name, or id.
        Only one role can be input, however it is not required.
        The reason can be any text.

        Usage:
        `?purge Nyx_2#8763 Xyphoer_id_here friend Retired`
        `?purge my_id_here Xyphoer_id_here Inactive`
        `?purge my_id_here`
        """
        for member in members:
            member.remove_roles(*member.roles, reason = reason)
            if role:
                member.add_roles(role, reason = reason)
        if members:
            if role: await ctx.send(f'Purged roles from {member.name for member in members}. Added role {role.name}. Reason: {reason}')
            else: await ctx.send(f'Purged roles from {member.name for member in members}. Reason: {reason}')

def setup(bot):
    bot.add_cog(Mod(bot))