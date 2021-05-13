from discord.ext import commands
import re

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