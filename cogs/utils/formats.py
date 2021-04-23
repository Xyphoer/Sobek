from discord.ext import commands

def compare_containers(*containers):
    shared = []

    for container in containers:
        for entry in container: shared.append(entry)

    for entry in shared:
        if shared.count(entry) < len(containers): shared.remove(entry)

    return shared