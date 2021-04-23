import discord
from discord.ext import tasks, commands
import asyncio
import math
import re
from asqlite import asqlite
from datetime import datetime, timezone
from typing import Optional
from .utils import formats, checks

class Utility(commands.Cog):
    """Commands orientated around general utility, such as certain role management, self editing, and message clearing."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        
        #Dragon, WS1-DA, WS2-DA, WS1-H, WS2-H
        tracked_roles = (444548579839705089, 700729258145742990, 713122732899827743, 621452020737507350, 713123165416718387)

        before_roles = formats.compare_containers(tracked_roles, before.roles)
        after_roles = formats.compare_containers(tracked_roles, after.roles)

        if not before_roles and not after_roles:
            return
        
        if before.raw_status == after.raw_status and before_roles == after_roles:
            return

        ws_role = False
        if formats.compare_containers(tracked_roles[1:]. before_roles) and not formats.compare_containers(tracked_roles[1:], after_roles): ws_role = datetime.now(timezone.utc)
        elif formats.compare_containers(tracked_roles[1:], after_roles): ws_role = 'Now'

        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT member FROM lastseen')
                m_id = await cursor.fetchall()
                m1 = [m[0] for m in m_id]

                if not after_roles:
                    await cursor.execute('DELETE FROM lastseen WHERE member=?', (member.id))
                    await conn.commit()
                    return

                if after.id in m1:
                    await cursor.execute('UPDATE lastseen SET status = ? WHERE member = ?', (after.raw_status, member.id))
                else:
                    await cursor.execute('INSERT INTO lastseen (member, status) VALUES(?, ?)', (member.id, after.raw_status))
                if ws_role:
                    await cursor.execute('UPDATE lastseen SET ws = ? WHERE member = ?', (ws_role, member.id))
                if before.raw_status != 'offline' and after.raw_status == 'offline':
                    await cursor.execute('UPDATE lastseen SET seen = ? WHERE member = ?', (datetime.now(timezone.utc), member.id))
                elif before.raw_status == 'offline' and after.raw_status != 'offline':
                    await cursor.execute('UPDATE lastseen SET seen = ? WHERE member = ?', ('Now', member.id))

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
            If the message is in the same channel however, just the message id is fine. If ?ws is specified with no members, and no member has the role, the message will be the last bot message (limit 10 messages) in white-star-preperation.
            The message will add all users who reacted to the message to the affected users.

        Ex:
            ?ws
            ?ws member1 member2
            ?ws member1 member2 role
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
                    try:
                        if role in member.roles:
                            await member.remove_roles(role)
                            removed.append(member.display_name)
                        else:
                            await member.add_roles(role)
                            added.append(member.display_name)

                    except discord.Forbidden:
                        await ctx.send(f'I have insufficient permissions to perform this task for {member.name}.')
                await ctx.send(f'`{role.name}`\nAdded: {", ".join(added)}\nRemoved: {", ".join(removed)}')
            else:
                await ctx.send(f"The specified role must be below your top role.")
        else:
            await ctx.send(f"Could not find role. Please ensure you're in the right category.")

    @commands.command()
    @checks.is_commander()
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
        allowed_channels = ('testing', 'orders', 'dump-n-grab', 'observations', 'rocket-support')
        if ctx.channel.name in allowed_channels:
            if members: final_message = f'Cleared from {amount if amount else "all"} messages, messages from {", ".join([member.name for member in members])}, oldest first = {old_first}.'
            else: final_message = f'Cleared from {amount if amount else "all"} messages, oldest first = {old_first}.'
            def check(m):
                if not members:
                    return m.pinned == False

                return m.pinned == False and m.author in members
            try:
                await ctx.message.delete()
                await ctx.channel.purge(limit=amount, check=check, oldest_first=old_first)
            except discord.Forbidden:
                await ctx.send('I am missing the required permissions to perform this actions.')
            else:
                await ctx.send(final_message, delete_after = 10.0)
        else:
            await ctx.send(f'Command not permitted in this channel.')

    @commands.command()
    async def WhiteStar(self, ctx, starting, category: discord.Role = None, size: int = 'Undetermined'):
        """Sends a new WhiteStar message to #white-star-preperation.

        Requires a a starting time.
        Can take in a role. If no role is specified will take the role associated with the channel category.
        Can take in an integer for the size of the star. If no integer is specified the size will be 'Undetermined'. You must specify a role if you wish to specify a size.
        
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
            commander = discord.utils.get(ctx.guild.roles, name='ws commander')
            if commander in ctx.author.roles:
                embed = discord.Embed(title='New White Star', 
                    description=f'__FC__: {ctx.author.mention}\n__Size__: {size}\n__Starting on__: {starting}\n__Category__: {category}')
                embed.set_footer(text="""
                    Please leave a reaction if you are interested in participating and will be able to respond within 1.5h of being pinged during your waking hours.
Note, reactions are simply to determine who will be the most active.
Anyone with their ws scanner on may be selected and will be expected to participate.
If you will not be able to respond within the 1.5h response time during your waking hours, but do not want to be left out of the star, contact the FC in general discussion.""")
                for channel in ctx.guild.channels:
                    if channel.name == 'white-star-preparation':
                        try:
                            await channel.send(f"""{ctx.guild.default_role} Below is an upcoming White Star. 
Please keep in mind that everyone is expeced to participate approximately once a month. 
If you are interested in leading a White Star, please contact an Officer or ws commander.""")
                            m = await channel.send(embed=embed)
                            await m.add_reaction('<:soldiersalute:614653371718041600>')
                            await ctx.send('Created.')
                        except discord.Forbidden:
                            await ctx.send('I do not have the appropriate permissions to perform this operation.')
                        return
                await ctx.send('Could not find `white-star-preparation`')
            else:
                await ctx.send('You must be a ws commander to use this command.')
        else:
            await ctx.send('No role was specified.')

    @commands.command()
    async def memorial(self, ctx, opponent, folder: discord.Role = None):
        """Creates a new ship memorial.
        
        Requires a specified opponent.
        Can take in a role. If no role is specified, takes the role associated with the channel category.
        If the opponent has a name longer than one word, wrap it in quotes.

        Order of inputs: opponent, role (optional)

        Examples:
            ?memorial Octoberpierynm
                --Creates a new memorial with opponent = Octoberpierynm, role = associated channel category.
            ?memorial "multi word opponent" @WS1 - DA
                --Creates a new memorial with opponent = Octoberpierynm, role = WS1 - DA.

        Note: Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        if folder == None:
            folder = discord.utils.get(ctx.guild.roles, name=f'{ctx.channel.category}')
        if folder != None:
            commander = discord.utils.get(ctx.guild.roles, name='ws commander')
            if commander in ctx.author.roles:
                embed = discord.Embed(title=f'{folder.name} vs {opponent} Memorial', color=0x7289DA)
                embed.add_field(name=f'__{folder.name} Losses__:\n(*Owner, Ship Type, Ship Name, Cause of Death, Time of Death, Time of Return*)', 
                    value='No losses yet.', inline=False)
                embed.add_field(name=f'__{opponent} Losses__:\n(*Owner, Ship Type, Ship Name, Cause of Death, Time of Death, Time of Return*)', 
                    value='No losses yet.', inline=False)
                embed.set_footer(text='''Use ?m to add losses to this message, for either side. 
When a new memorial is started, the old one will no longer be updated. 
When an enemy ship dies, a ping will be sent in #observations when their return time is up.''')
                category = discord.utils.get(ctx.guild.categories, name=f'{folder.name}')
                if category != None:
                    channel = discord.utils.get(category.channels, name=f'ship-memorial')
                    if channel != None:
                        try:
                            m = await channel.send(embed=embed)
                            await ctx.send(f'{folder.name} vs {opponent} Memorial created.')
                            folder1 = folder.name.replace(' ', '')
                            data_folder = folder1.replace('-', '_')
                            async with asqlite.connect('SobekStorage1.db') as conn:
                                async with conn.cursor() as cursor:
                                    await cursor.execute(f"UPDATE Memorial SET {data_folder} = '{m.id}' WHERE tracking = 1")
                                    await conn.commit()
                        except discord.Forbidden:
                            await ctx.send('I do not have the appropriate permissions to send the message.')
                    else:
                        await ctx.send(f'Could not find `ship-memorial` associated with `{folder.name}`.')
                else:
                    await ctx.send('Could not find associated category.')
            else:
                await ctx.send('You must be a ws commander to perform this action.')
        else:
            await ctx.send(f'Could not find role.')

    @commands.command()
    async def m(self, ctx, folder: discord.Role = None):
        """Adds to an existing ship memorial.

        Consists of a multi message proceedure to add lost ships for either side to a specific ship memorial.
        Can accept a role. Defaults to the role associated with the category of the channel in which it is called.

        Usage:
            ?m
            ?m @WS1 - DA
            ?m 700729258145742990

        Note: Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        if folder == None:
            folder = discord.utils.get(ctx.guild.roles, name=f'{ctx.channel.category}')
        if folder != None:
            commander = discord.utils.get(ctx.guild.roles, name='ws commander')
            if commander in ctx.author.roles:
                embed = discord.Embed(title=f'{folder.name} Ship Memorial',
                    description='Is this for:\n:one: Yours or an allies ship.\n:two: An opponents ship.',
                    color=0x7289DA)
                embed.set_footer(text='Timeout after 120s of inactivity.')

                timeout = discord.Embed(title=f'{folder.name} Ship Memorial',
                    description='Timed out.',
                    color=0x7289DA)

                first = await ctx.send(embed=embed)
                await first.add_reaction('1️⃣')
                await first.add_reaction('2️⃣')

                def check(reaction, user):
                    return user == ctx.author and (str(reaction.emoji) == '1️⃣' or str(reaction.emoji) == '2️⃣')

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check)
                except asyncio.TimeoutError:
                    await first.clear_reactions()
                    await first.edit(embed=timeout)
                else:
                    ally = False
                    if str(reaction.emoji) == '1️⃣':
                        ally = True
                    await first.clear_reactions()
                    embed1 = discord.Embed(title=f'{folder.name} Ship Memorial',
                        description='How long ago did the ship die?\n(Please respond with a decimal, representing hours. Ex. 3.4)',
                        color=0x7289DA)
                    embed1.set_footer(text='Timeout after 120s of inactivity.')
                    await first.edit(embed=embed1)

                    def check1(m):
                        return m.author == ctx.author and m.channel == ctx.channel

                    try:
                        second = await self.bot.wait_for('message', timeout=120.0, check=check1)
                    except asyncio.TimeoutError:
                        await first.edit(embed=timeout)
                    else:
                        time_ago = second.content
                        await second.delete()

                        try:
                            cooldown = 18
                            if decimal.Decimal(time_ago) != 0:
                                cooldown = 18 - decimal.Decimal(time_ago)
                            cooldown *=  3600
                        except decimal.InvalidOperation:
                            embed = discord.Embed(title=f'{folder.name} Ship Memorial', description='You message was not a decimal. Please start again.')
                            await first.edit(embed=embed)
                        else:

                            embed2 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                description='What is the name of the ships owner?',
                                color=0x7289DA)
                            embed1.set_footer(text='Timeout after 120s of inactivity.')
                            await first.edit(embed=embed2)

                            def check2(m):
                                return m.author == ctx.author and m.channel == ctx.channel

                            try:
                                third = await self.bot.wait_for('message', timeout=120.0, check=check2)
                            except asyncio.TimeoutError:
                                await first.edit(embed=timeout)
                            else:
                                ship_owner = third.content
                                await third.delete()

                                embed3 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                    description='Ship Type:\n:one: Battleship\n:two: Squishy',
                                    color=0x7289DA)
                                embed3.set_footer(text='Timeout after 120s of inactivity.')
                                await first.edit(embed=embed3)
                                await first.add_reaction('1️⃣')
                                await first.add_reaction('2️⃣')

                                def check3(reaction, user):
                                    return user == ctx.author and (str(reaction.emoji) in ['1️⃣', '2️⃣'])

                                try:
                                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check3)
                                except asyncio.TimeoutError:
                                    await first.clear_reactions()
                                    await first.edit(embed=timeout)
                                else:
                                    ship_type = 'Squishy'
                                    if str(reaction.emoji) == '1️⃣':
                                        ship_type = 'Battleship'
                                    await first.clear_reactions()

                                    embed4 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                        description="What is the ship's name?",
                                        color=0x7289DA)
                                    embed4.set_footer(text='Timeout after 120s of inactivity.')
                                    await first.edit(embed=embed4)

                                    try:
                                        fourth = await self.bot.wait_for('message', timeout=120.0, check=check2)
                                    except asycnio.TimeoutError:
                                        await first.edit(embed=timeout)
                                    else:
                                        ship_name = fourth.content
                                        await fourth.delete()

                                        embed5 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                            description='What is the time of death? (Format: days hours minutes (Ex. 3 8) (Time of death can be found by selecting the Star))',
                                            color=0x7289DA)
                                        embed5.set_footer(text='Timeout after 120s of inactivity.')
                                        await first.edit(embed=embed5)

                                        try:
                                            fifth = await self.bot.wait_for('message', timeout=120.0, check=check2)
                                        except asyncio.TimeoutError:
                                            await first.edit(embed=timeout)
                                        else:
                                            tod = re.findall('\d+', fifth.content)
                                            await fifth.delete()

                                            time_of_death = [0, 0, 0]
                                            for value in tod:
                                                if tod.index(value) < 3:
                                                    time_of_death[tod.index(value)] = int(value)
                                            r = (time_of_death[0] * 24 + time_of_death[1] - 18) / 24
                                            if r <= 0:
                                                r_day, r_hour, r_minute = [0, 0, 0]
                                            else:
                                                r_hour, r_day = math.modf(r)
                                                r_day, r_hour, r_minute = int(r_day), int(r_hour * 24), time_of_death[2]

                                            embed6 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                                description='What is the cause of death?',
                                                color=0x7289DA)
                                            embed6.set_footer(text='Timeout after 120s of inactivity.')
                                            await first.edit(embed=embed6)

                                            try:
                                                sixth = await self.bot.wait_for('message', timeout=120.0, check=check2)
                                            except asyncio.TimeoutError:
                                                await first.edit(embed=timeout)
                                            else:
                                                cause_of_death = sixth.content
                                                await sixth.delete()

                                                embed7 = discord.Embed(title=f'{folder.name} Ship Memorial',
                                                    description=f'Does this look correct?\n\n\
                                                    __Owner:__ {ship_owner}\n\
                                                    __Ship Type:__ {ship_type}\n\
                                                    __Ship Name:__ {ship_name}\n\
                                                    __Cause of Death:__ {cause_of_death}\n\
                                                    __Time of Death:__ {time_of_death[0]}d {time_of_death[1]}h {time_of_death[2]}m\n\
                                                    __Time of Return:__ {r_day}d {r_hour}h {r_minute}m',
                                                    color=0x7289DA)
                                                embed7.set_footer(text='Timeout after 120s of inactivity.')
                                                await first.edit(embed=embed7)
                                                await first.add_reaction('\U00002705')
                                                await first.add_reaction('\U0000274C')

                                                def check4(reaction, user):
                                                    return user == ctx.author and (str(reaction.emoji) == '\U00002705' or str(reaction.emoji) == '\U0000274C')

                                                try:
                                                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check4)
                                                except asyncio.TimeoutError:
                                                    await first.clear_reactions()
                                                    await first.edit(embed=timeout)
                                                else:
                                                    await first.clear_reactions()

                                                    if str(reaction.emoji) == '\U00002705':
                                                        category = discord.utils.get(ctx.guild.categories, name=f'{folder.name}')
                                                        if category != None:
                                                            memorial = discord.utils.get(category.channels, name='ship-memorial')
                                                            if memorial != None:
                                                                folder1 = folder.name.replace(' ', '')
                                                                data_folder = folder1.replace('-', '_')
                                                                async with asqlite.connect('SobekStorage1.db') as conn:
                                                                    async with conn.cursor() as cursor:
                                                                        await cursor.execute(f"SELECT {data_folder} FROM Memorial WHERE tracking = 1")
                                                                        m_id_tpl = await cursor.fetchone()
                                                                        m_id = m_id_tpl[0]
                                                                try:
                                                                    memorial_message = await memorial.fetch_message(m_id)
                                                                except (discord.NotFound, discord.Forbidden):
                                                                    await ctx.send('Could not find a memorial to edit. Ensure I have the proper permissions and/or a memorial exists to be edited.')
                                                                else:
                                                                    memorial_embed = memorial_message.embeds[0]
                                                                    memorial_dict = memorial_embed.to_dict()

                                                                    memorial_content = f'{ship_owner}, {ship_type}, {ship_name}, {cause_of_death}, {time_of_death[0]}d {time_of_death[1]}h {time_of_death[2]}m, {r_day}d {r_hour}h {r_minute}m'

                                                                    large = False

                                                                    if ally == True:
                                                                        if memorial_dict['fields'][0]['value'] == 'No losses yet.':
                                                                            memorial_dict['fields'][0]['value'] = f'{memorial_content}'
                                                                        else:
                                                                            memorial_dict['fields'][0]['value'] += f'\n\n{memorial_content}'
                                                                            if len(memorial_dict['fields'][0]['value']) > 1024:
                                                                                large = True
                                                                                memorial_dict['title'] += 'Continued'
                                                                                memorial_dict['fields'][0]['value'] = f'{memorial_content}'
                                                                    else:
                                                                        if memorial_dict['fields'][1]['value'] == 'No losses yet.':
                                                                            memorial_dict['fields'][1]['value'] = f'{memorial_content}'
                                                                        else:
                                                                            memorial_dict['fields'][1]['value'] += f'\n\n{memorial_content}'
                                                                            if len(memorial_dict['fields'][1]['value']) > 1024:
                                                                                large = True
                                                                                memorial_dict['title'] += 'Continued'
                                                                                memorial_dict['fields'][1]['value'] = f'{memorial_content}'
                                                                    memorial_final = discord.Embed.from_dict(memorial_dict)
                                                                    if large == True:
                                                                        new_memorial_message = await memorial_message.channel.send(embed=memorial_final)
                                                                        async with asqlite.connect('SobekStorage1.db') as conn:
                                                                            async with conn.cursor() as cursor:
                                                                                await cursor.execute(f"UPDATE Memorial SET {data_folder} = '{new_memorial_message.id}' WHERE tracking = 1")
                                                                                await conn.commit()
                                                                    else:
                                                                        await memorial_message.edit(embed=memorial_final)
                                                                    embed_submitted = discord.Embed(title=f'{folder.name} Ship Memorial', description='Submitted')
                                                                    await first.edit(embed=embed_submitted)

                                                                    observations = discord.utils.get(category.channels, name='observations')
                                                                    if observations != None:
                                                                        await asyncio.sleep(int(cooldown))
                                                                        await observations.send(f"{ship_owner}'s {ship_type} return time is up.")
                                                                    else:
                                                                        await ctx.send('observations channel not found.')
                                                            else:
                                                                await ctx.send(f'Could not find #ship-memorial in the category {category.name}.')
                                                        else:
                                                            await ctx.send(f'{folder.name} does not match any categories.')
                                                    else:
                                                        embedc = discord.Embed(title=f'{folder.name} Memorial', description='Cancelled.')
                                                        await first.edit(embed=embedc)
            else:
                await ctx.send('You must be a ws commander to perform this action.')
        else:
            await ctx.send(f'Could not find role.')

    @commands.command(aliases=['ls'])
    async def lastseen(self, ctx, sorting = 'a', members: commands.Greedy[discord.Member] = [], roles: commands.Greedy[discord.Role] = []):
        """Shows how long ago people were see in any status other than invisible/offline.

        Only members with the Dragon role are tracked.
        Can take an optional amount of members and/or roles. If no members or roles are specified defaults to everyone with the Dragon role.
        Has four methods of sorting. a (alphabetical), ar (alphabetical reverse), t (time), tr (time reverse). Defaults to a.
        
        Any specified roles must be after all (if any) specified members.
        Order of inputs: sorting (optional, a (alphabetical), ar (alphabetical reverse), t (time), tr (time reverse), w (ws activity), wr (ws activity reverse)) members (optional, any amount) roles (optional, any amount)

        Ex. ?ls member1 member2 "multi word role" role2
        Ex. ?lastseen role
        EX. ?ls tr member role1 role2
        
        Note: Members/Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        dragon = ctx.guild.get_role(444548579839705089) #444548579839705089
        member1 = []
        roles1 = []
        if sorting not in ('a', 'ar', 't', 'tr', 'w', 'wr'):
            try:
                sorting = await commands.MemberConverter().convert(ctx, str(sorting))
                member1.append(sorting)
                sorting = 'a'
            except Exception as e:
                print(e)
                try:
                    sorting = await commands.RoleConverter().convert(ctx, str(sorting))
                    roles1.append(sorting)
                    sorting = 'a'
                except:
                    await ctx.send(f'{sorting} is not recognized as as a sorting method. Defaulting to sorting method a.')
                    sorting = 'a'
        for x in members:
            member1.append(x)
        for x in roles:
            roles1.append(x)
        if roles1 == []:
            roles1 = [dragon]
        if member1 == []:
            for role in roles1:
                for memb in role.members:
                    member1.append(memb)
        elif roles1 != [dragon]:
            for role in roles1:
                for memb in role.members:
                    member1.append(memb)
        async with asqlite.connect('SobekStorage1.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM lastseen")
                m = await cursor.fetchall()
                m1 = {m0[0]: (m0[1], m0[2]) for m0 in m}
                final = {}
                for member in member1:
                    if member.id in m1:
                        container = []
                        for element in m1[member.id]:
                            if element != 'Never':
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
                            else:
                                container.append('Never')
                            final[f'{member.name} ({member.display_name})'] = ', __last ws__: '.join(container)
                send = []
                for record in final:
                    send.append(f'**{record}**: {final[record]}')

                def key_ago(info, index):
                    info = info.split(':')[index].strip(', __last ws__').strip().split()
                    if info == 'Now':
                        return 0
                    elif info == 'Never':
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
                    send.sort(key = str.lower)
                elif sorting.lower() == 'ar':
                    send.sort(key = str.lower, reverse=True)
                elif sorting.lower() == 't':
                    send.sort(key = lambda ago: key_ago(ago, 1))
                elif sorting.lower() == 'tr':
                    send.sort(key = lambda ago: key_ago(ago, 1), reverse=True)
                elif sorting.lower() == 'w':
                    send.sort(key = lambda ago: key_ago(ago, 2))
                elif sorting.lower() == 'wr':
                    send.sort(key = lambda ago: key_ago(ago, 2), reverse=True)

                ls_embed = discord.Embed(title='Last Seen',
                    description = '\n'.join(send))
                ls_embed.set_footer(text='If a mentioned member "has not been seen" they will not show up.\n'
                    'If a member is in the invisible status, their last seen time will be from their last time online in any status other than invisible\n'
                    'Unlisted members have never been seen.\n'
                    'Last Seen only applies to members with the Dragon role.')
                if len(ls_embed) <= 6000:
                    await ctx.send(embed=ls_embed)
                else:
                    await ctx.send('Embed is too long. Please specify role(s)/member(s) to get a shorter list.\n\
                        If this bothers you let Nyx_2#8763 (341331627839848448) know, and maybe a page feature will be implemented.')

    @commands.command(aliases=['rl'])
    async def rolelist(self, ctx, member: commands.Greedy[discord.Member] = [], role: commands.Greedy[discord.Role] = []):
        """Displays all roles/members associated with specified members/roles.

        Takes in amount of members and/or roles.
        All members must be specified first.

        Ex.
            ?rl member1 "member 2" role1

        Note: Members/Roles can be specified by mention, name, or id. Multi word names must be wrapped in quotes unless mentioned."""
        if member != []:
            member_list = ['Members with roles:']
            for memb in member:
                rl = []
                for role1 in memb.roles:
                    rl.append(f'`{role1.name}`')
                rl = ', '.join(rl)
                member_list.append(f'--{memb}({memb.display_name}):\n{rl}')
            await ctx.send('\n'.join(member_list))
        if role != []:
            role_list = ['Roles with members:']
            for rol in role:
                ml = []
                for member in rol.members:
                    ml.append(f'`{member}({member.display_name})`')
                ml = ', '.join(ml)
                role_list.append(f'--{rol}:\n{ml}')
            await ctx.send('\n'.join(role_list))
        elif role == [] and member == []:
            total_roles = []
            for role in ctx.guild.roles:
                total_roles.append(f'`{role.name}`')
            send_roles = ', '.join(total_roles)
            await ctx.send(f'Guild roles:\n{send_roles}')

    # @commands.command(hidden = True)   #not quite there yet...
    # @commands.is_owner()
    # async def eval(self, ctx, *, code):

    #     t = textwrap.indent(code.strip('```py'), '  ')
    #     code = f'async def code_func():\n{t}'

    #     vars = {
    #     'bot' : self.bot,
    #     'ctx' : ctx,
    #     }

    #     vars.update(globals())

    #     try:
    #         exec(code, vars)
    #         result = await code_func()
    #         await ctx.send(f'```py\n{result}```')
    #     except Exception as e:
    #         await ctx.send(f'```py\n{e}```')

def setup(bot):
    bot.add_cog(Utility(bot))