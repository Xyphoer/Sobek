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
    async def kick(self, ctx, members: commands.Greedy[discord.Member], *, reason = None):
        """
        Kicks the specified member(s) for the optional reason.

        Members can be specified by mention, name, or id.
        Reason can be any text.

        Usage:
        `?kick Nyx_2#8763 beligerent`
        `?kick 341331627839848448 Complete disregard for human decency`
        `?kick 341331627839848448 691827198251761735 just because`
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
    async def ban(self, ctx, members: commands.Greedy[discord.Member], purge_days: int = 0, *, reason = None):
        """
        Bans the specified member(s) for the optional reason, purging messages from the amount of days specified (max 7).

        Members can be specified by mention, name, or id.
        Purge_days can be an integer of 0 - 7.
        Reason can be any text.

        Usage:
        `?ban Nyx_2#8763 I can't even remember why.`
        `?ban 341331627839848448 2 Failure to please.`
        `?ban 341331627839848448 691827198251761735 1 In cahoots for global domination.`
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
    async def purge(self, ctx, members: commands.Greedy[discord.Member], role: Optional[discord.Role] = None, *, reason = None):
        """
        Purges all roles from specified members. Optionally add's a role as well. (Useful for converting members to friends)

        Members can be specified by mention, name, or id.
        Only one role can be input, however it is not required.
        The reason can be any text.

        Usage:
        `?purge Nyx_2#8763 691827198251761735 friend Retired`
        `?purge 341331627839848448 691827198251761735 Inactive`
        `?purge 341331627839848448`
        """
        if not members:
            await ctx.send('Specify a member to purge.')
            return
        
        for member in members:
            roles = [role for role in member.roles if role.name != '@everyone']
            await member.remove_roles(*roles, reason = reason)
            if role:
                await member.add_roles(role, reason = reason)
        if members:
            if role: await ctx.send(f'Purged roles from {", ".join(member.name for member in members)}. Added role {role.name}. Reason: {reason}')
            else: await ctx.send(f'Purged roles from {", ".join(member.name for member in members)}. Reason: {reason}')

    @commands.command(aliases = ['create_mute'])
    @checks.is_officer()
    async def create_mute_role(self, ctx):
        if 'muted' in [role.name for role in ctx.guild.roles]:
            mute_role = discord.utils.get(ctx.guild.roles, name = 'muted')
            for channel in ctx.guild.channels:
                if mute_role not in channel.overwrites: await channel.set_permissions(mute_role, reason = 'mute role update', send_messages = False)
            await ctx.send('"muted" role updated.')
        else:
            mute_role = await ctx.guild.create_role(reason = "mute role creation", name = 'muted')
            await mute_role.edit(position = ctx.guild.me.top_role.position - 1, reason = "updating mute role position")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, reason = 'mute role initialization', send_messages = False)

    @commands.command()
    @checks.is_officer()
    async def mute(self, ctx, members: commands.Greedy[discord.Member], *, reason = None):
        """
        Mutes one or multiple members for the optionally provided reason.

        Usage:
        `?mute Nyx_2`
        `?mute 341331627839848448 Nyx_2#8763 Can't stop bickering`
        """
        if not members:
            await ctx.send('Provide a member to mute.')
            return
        mute_role = discord.utils.get(ctx.guild.roles, name = 'muted')
        for member in members:
            await member.add_roles(mute_role, reason = f'Muted by {ctx.author.name} for reason: {reason}')
        await ctx.send(f'Muted {", ".join([member.name for member in members])}.')

    @commands.command()
    @checks.is_officer()
    async def unmute(self, ctx, members: commands.Greedy[discord.Member] = [], *, reason = None):
        """
        Unmutes one or multiple members for the optionally provided reason.

        Usage:
        `?unmute Nyx_2`
        `?unmute 341331627839848448 Nyx_2#8763 Issue resolved.`
        """
        if not members:
            await ctx.send('Provide a muted member to unmuted')
            return
        mute_role = discord.utils.get(ctx.guild.roles, name = 'muted')
        for member in members:
            await member.remove_roles(mute_role, reason = f'Unmuted by {ctx.author.name} for reason: {reason}')
        await ctx.send(f'Unmuted {", ".join([member.name for member in members])}')

    @commands.command()
    @checks.is_officer()
    async def lock(self, ctx):
        """
        Locks the channel the command is called in.

        Anyone without the Officer role can no longer send messages.
        No roles above the bots role will be changed.
        Member overrides are ignored.
        The lock and unlock commands aren't very advanced, so they may not work properly in certain circumstances.

        Usage: `?lock`
        """
        for role in ctx.channel.changed_roles:
            if role.id != 444548579839705089 and role.position < ctx.guild.me.top_role.position:
                await ctx.channel.set_permissions(role, reason = f"Channel lock by {ctx.author.name}", send_messages = False)
        await ctx.send('Channel locked.')

    @commands.command()
    @checks.is_officer()
    async def unlock(self ,ctx):
        """
        Unlocks the channel the command is called in.

        Anyone without the muted role can send messages once again.
        No roles above the bots role will be changed.
        Member overrides ignored.
        The lock and unlock commands aren't very advanced, so they may not work properly in certain circumstances.

        Usage: `?unlock`

        Note: The lock and unlock commands do not store previous channel overwrites, and therefore unlock may give the send_messages permissions to one or more roles that did not have it before the channel was locked.
        """
        mute_role = discord.utils.get(ctx.guild.roles, name = 'muted')
        for role in ctx.channel.changed_roles:
            if role != mute_role and role.position < ctx.guild.me.top_role.position:
                await ctx.channel.set_permissions(role, reason = f"Channel unlock by {ctx.author.name}", send_messages = True)
        await ctx.send('Channel unlocked.')

def setup(bot):
    bot.add_cog(Mod(bot))