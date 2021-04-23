from discord.ext import commands

def is_commander():
    def predicate(ctx):
        return 446277329300357122 in [role.id for role in ctx.author.roles] or ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)