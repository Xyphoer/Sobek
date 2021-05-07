import discord
from discord.ext import tasks, commands
import asyncio
import math
from asqlite import asqlite
from datetime import datetime, timezone
from typing import Optional
from .utils import formats, checks

class Utility(commands.Cog):
    """Commands orientated around general utility, such as certain role management, self editing, and message clearing."""

    def __init__(self, bot):
        self.bot = bot

    def role_list_process(self, title, total, container, individuals, color):

        embed = discord.Embed(title = title, description = " ".join(total), color = color)

        embed.add_field(name = 'Total', value = ' '.join(f'{content}: {container.count(content)}' for content in set(container)))
        embed.add_field(name = 'Individuals', value = individuals)
        if len(total) > 1:
            embed.add_field(name = 'Shared', value = " ".join(content for content in set(container) if container.count(content) == len(total)))

        return embed

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        
        #Dragon, WS1-DA, WS2-DA, WS1-H, WS2-H
        tracked_roles = (444548579839705089, 700729258145742990, 713122732899827743, 621452020737507350, 713123165416718387)

        before_roles = formats.compare_containers(tracked_roles, [role.id for role in before.roles])
        after_roles = formats.compare_containers(tracked_roles, [role.id for role in after.roles])

        if not before_roles and not after_roles:
            return
        
        if before.raw_status == after.raw_status and before_roles == after_roles:
            return

        ws_role = False
        if formats.compare_containers(tracked_roles[1:], before_roles) and not formats.compare_containers(tracked_roles[1:], after_roles): ws_role = datetime.now(timezone.utc)
        elif formats.compare_containers(tracked_roles[1:], after_roles): ws_role = 'Now'

        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT member FROM lastseen')
                m_id = await cursor.fetchall()
                m1 = [m[0] for m in m_id]

                if not after_roles:
                    await cursor.execute('DELETE FROM lastseen WHERE member=?', (after.id))
                    await conn.commit()
                    return

                if after.id in m1:
                    if after.raw_status != 'offline': await cursor.execute('UPDATE lastseen SET status = ? WHERE member = ?', (after.raw_status, after.id))
                    elif before.raw_status != 'offline': await cursor.execute('UPDATE lastseen SET status = ? WHERE member = ?', (before.raw_status, after.id))
                else:
                    await cursor.execute('INSERT INTO lastseen (member, seen, ws, status) VALUES(?, ?, ?, ?)', (after.id, 'Never' if after.raw_status == 'offline' else 'Now', 'Never', after.raw_status))
                if ws_role:
                    await cursor.execute('UPDATE lastseen SET ws = ? WHERE member = ?', (ws_role, after.id))
                if before.raw_status != 'offline' and after.raw_status == 'offline':
                    await cursor.execute('UPDATE lastseen SET seen = ? WHERE member = ?', (datetime.now(timezone.utc), after.id))
                elif before.raw_status == 'offline' and after.raw_status != 'offline':
                    await cursor.execute('UPDATE lastseen SET seen = ? WHERE member = ?', ('Now', after.id))

                await conn.commit()

    @commands.command(aliases = ['ws', 'er'])
    @checks.is_commander()
    async def edit_roles(self, ctx, role: Optional[discord.Role] = None, members: commands.Greedy[discord.Member] = [], prep_message: discord.Message = None):
        """Adds, removes, or clears a specific role for specified members.

        Adds or removes a specified role to/from specified members. 
        If no members are specified removes the role from all members with the specified role.
        If no role is specified defaults to the role assosiated with the category (if there is one).

        If a role is specified, it must be specified first.
        You can also specify a message at the end. If specified it must be of the format “{channel ID}-{message ID}” (retrieved by shift-clicking on “Copy ID”) or the message link.
            If the message is in the same channel however, just the message id is fine. If ?edit_roles is specified with no members, and no member has the role, the message will be the last bot message (limit 10 messages) in white-star-preperation.
            The message will add all users who reacted to the message to the affected users.

        Ex:
            ?ws
            ?ws member1 member2
            ?ws role member1 member2
            ?ws "muli word role"
            ?ws role 713126629358174338-793119635854589954

        Note: Members/Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        if role == None:
            role = discord.utils.get(ctx.guild.roles, name=f'{ctx.channel.category}')
        if members == []:
            members = role.members
            if members == []:
                preperation = self.bot.get_channel(713126629358174338)
                failed = True
                if prep_message:
                    try:
                        prep_message = commands.MessageConverter().convert(prep_message)
                        members = await prep_message.reactions[0].users().flatten()
                        if self.bot.user in members:
                            members.remove(self.bot.user)
                        failed = False
                    except:
                        await ctx.send(f'{prep_message} failed to match a message. Using {preperation.mention} last bot message.')
                if failed:
                    async for message in preperation.history(limit=10):
                        if message.author == self.bot.user:
                            members = await message.reactions[0].users().flatten()
                            if self.bot.user in members:
                                members.remove(self.bot.user)
                            break
                    else:
                        await ctx.send(f'Could not find a preperation message in the last 10 messages in {preperation.mention}.')
        if role != None:
            if role.position < ctx.author.top_role.position:
                added = []
                removed = []

                for member in members:
                    if role in member.roles:
                        await member.remove_roles(role)
                        removed.append(member.display_name)
                    else:
                        await member.add_roles(role)
                        added.append(member.display_name)
                await ctx.send(f'`{role.name}`\nAdded: {", ".join(added)}\nRemoved: {", ".join(removed)}')
            else:
                await ctx.send(f"The specified role must be below your top role.")
        else:
            await ctx.send(f"Could not find role. Please ensure you're in the right category.")

    @commands.command()
    @checks.is_commander()
    @checks.allowed_channels('testing', 'orders', 'dump-n-grab', 'observations', 'rocket-support')
    async def clear(self, ctx, amount: Optional[int] = None, old_first: Optional[bool] = True, members: commands.Greedy[discord.Member] = None):
        """Clears all or a specified amount (to search through) of messages in a channel.

        Provide no arguments to clear all. 
        Ex. `?clear`
        Provide an integer to clear from a specified amount. 
        Ex. `?clear 10`
        Provide "True" or "False" to change between oldest first, and newest first. Default is true, which corresponds to oldest first.
        Ex. `?clear 10 False`
        Provide any number of members (via id, mention, or display name) to only remove messages from those members.
        Ex. `?clear 10 False 341331627839848448`
        No arguments are required. You may leave out any arguments and provide the others, so long as you maintain the proper order for the arguments you do provide.

        Never clears pinned messages."""
        if members: final_message = f'Cleared from {amount if amount else "all"} messages, messages from {", ".join([member.name for member in members])}, oldest first = {old_first}.'
        else: final_message = f'Cleared from {amount if amount else "all"} messages, oldest first = {old_first}.'
        def check(m):
            if not members:
                return m.pinned == False

            return m.pinned == False and m.author in members
        await ctx.message.delete()
        await ctx.channel.purge(limit=amount, check=check, oldest_first=old_first)
        await ctx.send(final_message, delete_after = 10.0)

    @commands.command()
    @checks.is_commander()
    @checks.blocked_channels('lobby', 'red-star')
    async def WhiteStar(self, ctx, starting, category: Optional[discord.Role] = None, size: Optional[int] = 'Undetermined', *, comment = None):
        """Sends a new WhiteStar message to #white-star-preperation.

        Requires a a starting time.
        Can take in a role. If no role is specified will take the role associated with the channel category.
        Can take in an integer for the size of the star. If no integer is specified the size will be 'Undetermined'.
        Can take in an optional comment to be included.
        
        Order of inputs: starting, role (optional), size (optional)

        Examples:
            ?WhiteStar tomorrow
                --New ws message starting tomorrow, role = category role, size = Undetermined
            ?WhiteStar 23/11/2020 @WS1 - DA
                --New ws message starting 23/11/2020, role = WS1 - DA, size = Undetermined
            ?WhiteStar Friday 621452020737507350 15
                --New ws message starting Friday, role = WS1 - H (Note, using the role id is equivilant to mentioning the role), size = 15

        Note: Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        if category == None:
            category = discord.utils.get(ctx.guild.roles, name=f'{ctx.channel.category}')
        if category != None:
            comm = ''
            if comment: comm = f'__Comment__: {comment}'
            embed = discord.Embed(title='New White Star', 
                description=f'__FC__: {ctx.author.mention}\n__Size__: {size}\n__Starting on__: {starting}\n__Category__: {category.mention}\n{comm}')
            embed.set_footer(text="""
                Please leave a reaction if you are interested in participating and will be able to respond within 1.5h of being pinged during your waking hours.
Note, reactions are simply to determine who will be the most active.
Anyone with their ws scanner on may be selected and will be expected to participate.
If you will not be able to respond within the 1.5h response time during your waking hours, but do not want to be left out of the star, contact the FC in general discussion.""")
            channel = self.bot.get_channel(713126629358174338)
            dragon = ctx.guild.get_role(444548579839705089)
            if channel:
                await channel.send(f"""{dragon.mention} Below is an upcoming White Star. 
Please keep in mind that everyone is expeced to participate approximately once a month. 
If you are interested in leading a White Star, please contact an Officer or ws commander.""")
                m = await channel.send(embed=embed)
                await m.add_reaction('<:soldiersalute:614653371718041600>')
                await ctx.send('Created.')
            else: await ctx.send('Could not find `white-star-preparation`')
        else:
            await ctx.send('No role was specified.')

    @commands.command()
    async def test(self, ctx):
        paginator = commands.Paginator(prefix = '', suffix = '')
        for x in range(5):
            paginator.add_line(str(x))
        await ctx.send(paginator.pages)

    @commands.command(aliases=['ls'])
    @checks.is_dragon(ws_allowed = True)
    @checks.blocked_channels('lobby', 'mess-hall', 'red-star')
    async def lastseen(self, ctx, sorting = 'a', members: commands.Greedy[discord.Member] = [], roles: commands.Greedy[discord.Role] = []):
        """Shows how long ago people were see in any status other than invisible/offline.

        Only members with the Dragon role are tracked.
        Can take an optional amount of members and/or roles. If no members or roles are specified defaults to everyone with the Dragon role.
        Has four methods of sorting. a (alphabetical), ar (alphabetical reverse), t (time), tr (time reverse). Defaults to a.
        
        Any specified roles must be after all (if any) specified members.
        Order of inputs: sorting (optional, a (alphabetical), ar (alphabetical reverse), t (time), tr (time reverse), w (ws activity), wr (ws activity reverse)) members (optional, any amount) roles (optional, any amount)

        Ex. 
            `?ls member1 member2 "multi word role" role2`
            `?lastseen role`
            `?ls tr member role1 role2`
        
        Note: Members/Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        status = {
        'online' : '<:status_online:830914158387527681>',
        'streaming' : '<:status_streaming:830914213860999198>',
        'dnd' : '<:status_dnd:830914192294674485>',
        'idle' : '<:status_idle:830914177937047612>',
        'offline' : '<:status_offline:835534710297198602>'
        }

        member1 = set()
        roles1 = set()
        if sorting not in ('a', 'ar', 't', 'tr', 'w', 'wr'):
            try:
                sorting = await commands.MemberConverter().convert(ctx, str(sorting))
                member1.add(sorting)
            except Exception as e:
                try:
                    sorting = await commands.RoleConverter().convert(ctx, str(sorting))
                    roles1.add(sorting)
                except:
                    await ctx.send(f'{sorting} is not recognized as as a sorting method. Defaulting to sorting method a.')
            finally:
                sorting = 'a'
        for x in members:
            member1.add(x)
        for x in roles:
            roles1.add(x)
        for role in roles1:
            for member in role.members:
                member1.add(member)
        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM lastseen")
                m = await cursor.fetchall()
                m1 = {m0[0]: (m0[1], m0[2], m0[3]) for m0 in m}
                final = {}
                for memb in member1 if member1 else m1:
                    member = memb

                    if type(member) == int:
                        member = ctx.guild.get_member(member)
                        if not member:
                            await cursor.execute('DELETE FROM lastseen WHERE member=?', (memb))
                            continue

                    if member.id in m1:
                        container = []
                        for element in m1[member.id]:
                            try:
                                datetime_object = datetime.strptime(element, '%Y-%m-%d %H:%M:%S.%f%z')
                                delta_difference = datetime.now(timezone.utc) - datetime_object
                                m_amount, h_amount = math.modf(delta_difference.seconds / 3600)
                                days, hours, minutes = delta_difference.days, int(h_amount), int(m_amount * 60)
                                if days != 0:
                                    time_since_seen = f'{days}d {hours}h {minutes}m'
                                elif hours != 0:
                                    time_since_seen = f'{hours}h {minutes}m'
                                elif minutes != 0:
                                    time_since_seen = f'{minutes}m'
                                else:
                                    time_since_seen = 'Now'
                                container.append(time_since_seen)
                            except ValueError:
                                container.append(element)
                        final[f'{status[container[-1]]} {member.mention}'] = ', __last ws__: '.join(container[:-1])
                send = []
                for record in final:
                    send.append(f'**{record}**: {final[record]}')

                def key_ago(info, index):
                    info = info.split(':')[index].strip(', __last ws__').strip().split()
                    if info[0] == 'No':
                        return 0
                    elif info[0] == 'Never':
                        return float('inf')
                    total_ago = 0
                    for amount in info:
                        if 'd' in amount:
                            total_ago += int(amount.strip('d')) * 1440
                        if 'h' in amount:
                            total_ago += int(amount.strip('h')) * 60
                        if 'm' in amount:
                            total_ago += int(amount.strip('m'))
                    return total_ago

                if sorting.lower() == 'a':
                    send.sort(key = lambda ago: str.lower(ago.split('>')[-1]))
                elif sorting.lower() == 'ar':
                    send.sort(key = lambda ago: str.lower(ago.split('>')[-1]), reverse=True)
                elif sorting.lower() == 't':
                    send.sort(key = lambda ago: key_ago(ago.split('>')[-1], 1))
                elif sorting.lower() == 'tr':
                    send.sort(key = lambda ago: key_ago(ago.split('>')[-1], 1), reverse=True)
                elif sorting.lower() == 'w':
                    send.sort(key = lambda ago: key_ago(ago.split('>')[-1], 2))
                elif sorting.lower() == 'wr':
                    send.sort(key = lambda ago: key_ago(ago.split('>')[-1], 2), reverse=True)

                paginator = commands.Paginator(prefix = '', suffix = '')

                for entry in send:
                    paginator.add_line(entry)

                pages = {}
                index = 1

                for page in paginator.pages:

                    ls_embed = discord.Embed(title='Last Seen',
                        description = page)
                    ls_embed.set_footer(text='If a mentioned member "has not been seen" or is not tracked they will not show up.\n'
                        'If a member is in the invisible status, their last seen time will be from their last time online in any status other than invisible\n'
                        'The displayed status is the last status they were seen in other than offline (offline may appear in rare circumstances).\n'
                        'Last Seen only applies to members with the Dragon role or a ws role.\n'
                        f'Page {index}/{len(paginator.pages)}')

                    pages[index] = ls_embed
                    index += 1

                index = 1
                message = await ctx.send(embed = pages[index])

                if len(pages) > 1:
                    await message.add_reaction('◀️')
                    await message.add_reaction('▶️')

                    def check(reaction, user):
                        return user == ctx.author and str(reaction.emoji) in ('◀️', '▶️')

                    while True:
                        try:
                            reaction, user = await self.bot.wait_for('reaction_add', timeout = 60.0, check = check)
                        except asyncio.TimeoutError:
                            await message.clear_reactions()
                            break
                        else:
                            await message.remove_reaction(reaction, ctx.author)
                            if str(reaction.emoji) == '▶️' and index < len(pages):
                                index += 1
                                await message.edit(embed = pages[index])
                            elif str(reaction.emoji) == '◀️' and index > 1:
                                index -= 1
                                await message.edit(embed = pages[index])

    @commands.command(aliases=['rl'])
    async def rolelist(self, ctx, members: commands.Greedy[discord.Member] = [], roles: commands.Greedy[discord.Role] = [], ids: bool = False):
        """Displays all roles/members associated with specified members/roles, along with some useful information.

        Takes in amount of members and/or roles.
        All members must be specified first.
        Accepts an optional bool value of True or False at the end for whether or not to have the fields use ids. Defaults to False
        If no members/roles are specified, lists the guild roles.

        Displayed fields are:
        Total (all roles on specified members or all members with a specified role),
        Individuals (all specified members and their roles or all specified roles and their members)
        Shared (all roles on all specified members or all members)

        Ex.
            `?rl member1 "member 2" role1`
            `?rolelist`
            `?rolelist 621452020737507350 True`

        Note: Members/Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        
        individual_roles = zip(set(members), [member.roles for member in set(members)])
        individual_members = zip(set(roles), [role.members for role in set(roles)])

        if ids:
            member_roles = [str(role.id) for role in formats.no_nested_containers([member.roles for member in members])]
            members_total = [str(member.id) for member in set(members)]
            individual_roles = "\n\n".join([f'{str(member.id)}: {" ".join(str(role.id) for role in roles)}' for member, roles in individual_roles])

            role_members = [str(member.id) for member in formats.no_nested_containers([role.members for role in roles])]
            roles_total = [str(role.id) for role in set(roles)]
            individual_members = "\n\n".join([f'{str(role.id)}: {" ".join(str(member.id) for member in members)}' for role, members in individual_members])
        else:
            member_roles = [role.mention for role in formats.no_nested_containers([member.roles for member in members])]
            members_total = [member.mention for member in set(members)]
            individual_roles = "\n\n".join([f'{member.mention}: {" ".join(role.mention for role in roles)}' for member, roles in individual_roles])

            role_members = [member.mention for member in formats.no_nested_containers([role.members for role in roles])]
            roles_total = [role.mention for role in set(roles)]
            individual_members = "\n\n".join([f'{role.mention}: {" ".join(member.mention for member in members)}' for role, members in individual_members])


        if members:
            if member_roles:
                embed_members = self.role_list_process('Members with roles:', members_total, member_roles, individual_roles, ctx.author.top_role.color.value)
                await ctx.send(embed = embed_members)
            else:
                await ctx.send(f'No roles assigned to {", ".join(members_total)}')

        if roles:
            if role_members:
                embed_roles = self.role_list_process('Roles with members:', roles_total, role_members, individual_members, ctx.author.top_role.color.value)
                await ctx.send(embed = embed_roles)
            else:
                await ctx.send(f'No members assigned to {", ".join(roles_total)}')

        elif not members:
            if ids:
                embed_guild_roles.add_field(title = 'Guild Roles ids', value = " ".join(role.id for role in ctx.guild.roles))

            else:
                embed_guild_roles = discord.Embed(title = 'Guild Roles:', description = ' '.join(role.mention for role in ctx.guild.roles), color = ctx.author.top_role.color.value)

            await ctx.send(embed = embed_guild_roles)

def setup(bot):
    bot.add_cog(Utility(bot))
