from discord.ext import commands

def compare_containers(*containers):
    shared = []

    for container in containers:
        for entry in container: shared.append(entry)

    for entry in shared:
        if shared.count(entry) < len(containers): shared.remove(entry)

    return shared

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