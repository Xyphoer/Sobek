from discord.ext import commands

def is_dragon():
    def predicate(ctx):
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