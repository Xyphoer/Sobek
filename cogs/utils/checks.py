from discord.ext import commands
import formats

def is_dragon(ws_allowed = False):
    def predicate(ctx):
        if ws_allowed:
            return formats.one_or_more((444548579839705089, 700729258145742990, 713122732899827743, 621452020737507350, 713123165416718387), [role.id for role in ctx.author.roles]) or ctx.author.guild_permissions.manage_roles
        return 444548579839705089 in [role.id for role in ctx.author.roles] or ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)

def is_commander():
    def predicate(ctx):
        return 446277329300357122 in [role.id for role in ctx.author.roles] or ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)

def is_officer():
    def predicate(ctx):
        return 447816270310801439 in [role.id for role in ctx.author.roles] or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def allowed_channels(*channels):
    def predicate(ctx):
        return ctx.channel.name in channels or ctx.author.id == 341331627839848448
    return commands.check(predicate)

def blocked_channels(*channels):
    def predicate(ctx):
        return ctx.channel.name not in channels or ctx.author.id == 341331627839848448
    return commands.check(predicate)