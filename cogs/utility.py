import discord
from discord.ext import tasks, commands
import asyncio
import math
import argparse
from asqlite import asqlite
from datetime import datetime, timezone, timedelta
from typing import Optional
from .utils import formats, checks

class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)

class LastSeen:
    """Class to process and handle information regarding tracked members for the lastseen command."""

    status_chart = {
    'online' : '<:status_online:830914158387527681>',
    'streaming' : '<:status_streaming:830914213860999198>',
    'dnd' : '<:status_dnd:830914192294674485>',
    'idle' : '<:status_idle:830914177937047612>',
    'offline' : '<:status_offline:835534710297198602>'
    }

    def __init__(self, member, stored_time, ws_time, status):
        self.member = member

        self.name = member.name

        try:
            self.passed_time = self.process_time(stored_time)
        except ValueError:
            self.passed_time = stored_time

        try:
            self.passed_ws_time = self.process_time(ws_time)
        except ValueError:
            self.passed_ws_time = ws_time

        self.status = status

        self.sendable = f'{self.status_chart[self.status]}{self.member.mention}: {self.passed_time}, __last ws__: {self.passed_ws_time}'

    def process_time(self, time):
        passed_time = datetime.now(timezone.utc) - datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f%z')
        m_amount, h_amount = math.modf(passed_time.seconds / 3600)
        days, hours, minutes = passed_time.days, int(h_amount), int(m_amount * 60)
        if days != 0:
            time_since_seen = f'{days}d {hours}h {minutes}m'
        elif hours != 0:
            time_since_seen = f'{hours}h {minutes}m'
        elif minutes != 0:
            time_since_seen = f'{minutes}m'
        else:
            time_since_seen = 'Now'

        return time_since_seen

    def sorting(self, method):
        if method == 'a':
            return self.name

        elif method == 't':
            if self.passed_time == 'Now':
                return 0
            elif self.passed_time == 'Never':
                return float('inf')
            else:
                return self.passed_time

        elif method == 'w':
            if self.passed_ws_time == 'Now':
                return 0
            elif self.passed_ws_time == 'Never':
                return float('inf')
            else:
                return self.passed_ws_time

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
        
        #Dragon, WS1-DA, WS2-DA, WS1-H, WS2-H (444548579839705089, 700729258145742990, 713122732899827743, 621452020737507350, 713123165416718387)
        tracked_roles = (444548579839705089, 700729258145742990, 713122732899827743, 621452020737507350, 713123165416718387)

        before_roles = formats.compare_containers(tracked_roles, [role.id for role in before.roles])
        after_roles = formats.compare_containers(tracked_roles, [role.id for role in after.roles])

        if before.raw_status != after.raw_status:
            async with asqlite.connect('SobekStorage1.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute('SELECT * FROM notify')
                    row_info = await cursor.fetchall()
                    m_id = {m[0]: m[1:] for m in row_info}
                    if after.id in m_id and after.raw_status != 'offline':
                        await formats.process_notify(self, after, *m_id[after.id])
                        await cursor.execute('DELETE FROM notify WHERE member=?', (after.id))
                        await conn.commit()

        if before.raw_status == after.raw_status and before_roles == after_roles:
            return

        if not before_roles and not after_roles:
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
    async def clear(self, ctx, amount: Optional[int] = None, *args):
        """Clears all or a specified amount (to search through) of messages in a channel.

        The amount provided is the amount the bot will search through. This is not necissarily the amount it will delete.

        **Simple Usage:**
        Provide no arguments to clear all. 
        Ex. `?clear`
        Provide an integer to clear from a specified amount. 
        Ex. `?clear 10`
        
        **Advanced Usage:**
        These are all optional parameters.
        
        `--members`   : alias `-m`. One or more members to delete messages from (will ignore all other messages).
        `--before`    : alias `-b`. A message or time ago. Only deletes messages before the specified message or time.
        `--after`     : alias `-a`. A message or time ago. Only deletes messages after the specified message or time.
        `--new-first` : alias `-n`. If provided will delete newer messages first as opposed to the default old first.

        Members can be specified by id, mention, name, etc.
        Messages can be specified by id, link, or channel_id-message_id
        Time ago must be specified like so: "`x`d`x`h`x`m". No spaces, replace `x` with an integer or decimal. (Same way it's specified for `?remind`)
        
        Examples:
        `?clear 5 --members 677533623808819230 341331627839848448 -b 30m`
        `?clear -n --after 841036302522384437 --before 50m` (Note that if the `after` message here is earlier than 50m ago nothing will be deleted)

        Never clears pinned messages."""
        parser = Arguments(description = 'Parser for the clear command.', add_help = False, allow_abbrev = False)

        parser.add_argument('-m', '--members', action = 'append', nargs = '+')
        parser.add_argument('-b', '--before')
        parser.add_argument('-a', '--after')
        parser.add_argument('-n', '--new-first', dest = 'old_first', action = 'store_false', default = True)

        try:
            args = parser.parse_args(args)
        except Exception as e:
            return await ctx.send(str(e))

        members = []
        if args.members:
            args.members = formats.no_nested_containers(args.members)
            try:
                for member in args.members:
                    members.append(await commands.MemberConverter().convert(ctx, member))
            except commands.MemberNotFound:
                await ctx.send('Could not find member ', member)
                return


        async def converter(message):
            try:
                return await commands.MessageConverter().convert(ctx, message)
            except Exception:
                return formats.time_converter(message)

        if args.before:
            args.before = await converter(args.before)
            if not args.before:
                await ctx.send('Cannot understand `--before` input. Allowed formats are a message or a length of time ago.')
                return
            if type(args.before) != discord.Message:
                args.before = datetime.utcnow() - timedelta(days = args.before['days'], hours = args.before['hours'], minutes = args.before['minutes'])
        if args.after:
            args.after = await converter(args.after)
            if not args.after:
                await ctx.send('Cannot understand `--after` input. Allowed formats are a message or a length of time ago.')
                return
            if type(args.after) != discord.Message:
                args.after = datetime.utcnow() - timedelta(days = args.after['days'], hours = args.after['hours'], minutes = args.after['minutes'])

        def check(m):
            if not members:
                return m.pinned == False

            return m.pinned == False and m.author in members

        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit = amount, check = check, before = args.before, after = args.after, oldest_first = args.old_first)
        
        if members: await ctx.send(f'Cleared {len(deleted)} messages from {amount if amount else "all"} messages, messages from {", ".join([member.name for member in members])}, {"oldest first" if args.old_first else "newest first"}.', delete_after = 8.0)
        else: await ctx.send(f'Cleared {len(deleted)} messages from {amount if amount else "all"} messages, {"oldest first" if args.old_first else "newest first"}.', delete_after = 8.0)

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

        member1 = set()
        roles1 = set()
        if sorting not in ('a', 'ar', 't', 'tr', 'w', 'wr'):
            try:
                sorting = await commands.MemberConverter().convert(ctx, str(sorting))
                member1.add(sorting)
            except:
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

                final = []
                for memb in member1 if member1 else m1:
                    member = memb

                    if type(member) == int:
                        member = ctx.guild.get_member(member)
                        if not member:
                            await cursor.execute('DELETE FROM lastseen WHERE member=?', (memb))
                            continue

                    if member.id in m1:
                        stored_time, ws_time, status = m1[member.id]
                        final.append(LastSeen(member, stored_time, ws_time, status))

        if 'r' in sorting:
            final.sort(key = lambda ago: ago.sorting(sorting[0]), reverse = True)
        else:
            final.sort(key = lambda ago: ago.sorting(sorting))

        send = []
        for obj in final:
            send.append(obj.sendable)

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
        if len(pages):
            message = await ctx.send(embed = pages[index])
        else:
            await ctx.send('No recorded activity.')

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

    @commands.command()
    @checks.is_dragon(ws_allowed = True)
    async def notify(self, ctx, member: discord.Member):
        """Pings you when the specified member is no longer offline.

        Usage:
        `?notify 341331627839848448`
        `?notify @Nyx_2#8763`
        """
        if member.raw_status != 'offline':
            await ctx.send(f'{member.name}#{member.discriminator} is currently online.')
            return

        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('INSERT INTO notify (member, author, channel, time_now, url) VALUES (?, ?, ?, ?, ?)', (member.id, ctx.author.id, ctx.channel.id, datetime.now(timezone.utc), ctx.message.jump_url))

        await ctx.send(f'You will be notified when {member.name}#{member.discriminator} is no longer offline.')

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

    @commands.command()
    @commands.is_owner()
    async def edit_lastseen(self, ctx, member: discord.Member, seen_type, time_ago, track = False):
        if seen_type != 'seen' and seen_type != 'ws':
            await ctx.send(f'Invalid type `{type}`, valid types are:\nseen\nws')
            return
        
        if track = 'y':
            track = True

        detailed_amount = formats.time_converter(time_ago)

        if not detailed_amount:
            await ctx.send('Invalid time: make sure to format each amount of time with the appropriate letter.')
            return
        
        delta_time = timedelta(days = detailed_amount['days'], hours = detailed_amount['hours'], minutes = detailed_amount['minutes'])
        
        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT member FROM lastseen')
                m_id = await cursor.fetchall()
                m1 = [m[0] for m in m_id]

                if member.id not in m1 and track:
                    await cursor.execute('INSERT INTO lastseen (member, seen, ws, status) VALUES(?, ?, ?, ?)', (member.id, 'Never', 'Never', member.raw_status))

                if member.id not in m1 and not track:
                    await ctx.send('Member not tracked.')
                elif seen_type == 'seen':
                    await cursor.execute('UPDATE lastseen SET seen = ? WHERE member = ?', (datetime.now(timezone.utc) - delta_time, member.id))
                elif seen_type == 'ws':
                    await cursor.execute('UPDATE lastseen SET ws = ? WHERE member = ?', (datetime.now(timezone.utc) - delta_time, member.id))
                await ctx.send('Member info updated')

def setup(bot):
    bot.add_cog(Utility(bot))
