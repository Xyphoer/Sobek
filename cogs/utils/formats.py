from discord.ext import commands
import re
from datetime import datetime, timezone

def compare_containers(*containers):
    total = []
    shared = []

    for container in containers:
        for entry in container: total.append(entry)

    for entry in total:
        if total.count(entry) == len(containers): shared.append(entry)

    return set(shared)

def no_nested_containers(container):
    container = list(container)
    clean = False
    while not clean:
        clean = True
        for content in container:
            if type(content) in (set, tuple, list):
                for value in content: container.insert(container.index(content), value)
                container.remove(content)
                clean = False
    return container

def one_or_more(matches, container):
    for content in container:
        for match in matches:
            if content == match:
                return True
    return False

def time_converter(duration):
    regex_type = re.compile(r'd|h|m')
    regex_amount = re.compile(r'(\d+\.?\d*)|(\.\d+)')
    style = regex_type.findall(duration.lower())
    time_full = regex_amount.findall(duration.lower())
    time = []
    value = {}
    for y in time_full:
        for x in y:
            if x != '':
                time.append(x)
    value['days'], value['hours'], value['minutes'] = (0, 0, 0)
    if len(style) < len(time):
        return False
    for amount in time.copy():
        if style[time.index(amount)] == 'd' and value['days'] == 0:
            value['days'] = float(amount)
            time.remove(amount)
            style.remove('d')
        elif style[time.index(amount)] == 'h' and value['hours'] == 0:
            value['hours'] = float(amount)
            time.remove(amount)
            style.remove('h')
        elif style[time.index(amount)] == 'm' and value['minutes'] == 0:
            value['minutes'] = float(amount)
            time.remove(amount)
            style.remove('m')
    value['total time'] = value['days'] * 86400 + value['hours'] * 3600 + value['minutes'] * 60

    if not value['total time']:
        return False

    return value

async def process_notify(self, member, author, channel, time_then, url):
    channel = self.bot.get_channel(channel)
    if not channel:
        return

    author = self.bot.get_user(author)
    if not author:
        return

    time_then = datetime.strptime(time_then, '%Y-%m-%d %H:%M:%S.%f%z')

    time_difference = datetime.now(timezone.utc) - time_then
    total_seconds = int(time_difference.total_seconds())
    
    days = int(total_seconds / 86400)
    total_seconds -= days * 86400

    hours = int(total_seconds / 3600)
    total_seconds -= hours * 3600

    minutes = int(total_seconds / 60)
    total_seconds -= minutes * 60

    days = f'{days}d' if days else ''
    hours = f'{hours}h' if hours else ''
    minutes = f'{minutes}m' if minutes else ''

    await channel.send(f'{author.mention} {member.mention} is no longer offline.\n\
    Notification from {days}{hours}{minutes}{total_seconds}s ago.\n\
    {url}')