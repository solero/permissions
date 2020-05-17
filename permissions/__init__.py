from houdini.plugins import IPlugin
from houdini import commands

from houdini import permissions
from houdini.data.penguin import Penguin
from houdini.data import db
from houdini.data.permission import Permission, PenguinPermission


class Permissions(IPlugin):
    author = "Solero"
    description = "Permissions management plugin"
    version = "1.0.0"

    def __init__(self, server):
        super().__init__(server)

    async def ready(self):
        await self.server.permissions.register('permissions.read')
        await self.server.permissions.register('permissions.write')

    @commands.group('p')
    async def _permissions(self, p):
        pass

    @_permissions.command('own')
    @permissions.has_or_moderator('permissions')
    async def take_ownership(self, p):
        permissions_assigned = await db.select([db.func.count(PenguinPermission.penguin_id)]).gino.scalar()
        if not permissions_assigned:
            await p.add_permission(self.server.permissions['permissions'])
            await p.send_xt('mm', f'Player \'{p.username}\' has full control', p.id)
        elif 'permissions' in p.permissions:
            await p.send_xt('mm', 'You already have full control', p.id)
        else:
            await p.send_xt('mm', 'You cannot take control of this server', p.id)

    @_permissions.command('add', alias=['a', 'assign'])
    @permissions.has('permissions.write')
    async def add_permission(self, p, target: str.lower, permission: Permission):
        if permission is None:
            return await p.send_xt('mm', 'Permission does not exist!', p.id)

        if target in p.server.penguins_by_username:
            target_penguin = p.server.penguins_by_username[target]
            await target_penguin.add_permission(permission)
        else:
            target_penguin = await Penguin.query.where(Penguin.username == target).gino.first()
            await PenguinPermission.create(penguin_id=target_penguin.id, permission_name=permission.name)

        await p.send_xt('mm', f'Assigned permission \'{permission.name}\' to user \'{target_penguin.username}\'', p.id)

    @_permissions.command('revoke', alias=['r', 'remove'])
    @permissions.has('permissions.write')
    async def revoke_permission(self, p, target: str.lower, permission: Permission):
        if permission is None:
            return await p.send_xt('mm', 'Permission does not exist!', p.id)

        if target in p.server.penguins_by_username:
            target_penguin = p.server.penguins_by_username[target]
            await target_penguin.revoke_permission(permission)
        else:
            target_penguin = await Penguin.query.where(Penguin.username == target).gino.first()
            await PenguinPermission.delete.where(
                (PenguinPermission.penguin_id == target_penguin.id) &
                ((PenguinPermission.permission_name.like(permission.name + '.%')) |
                 (PenguinPermission.permission_name == permission.name))).gino.status()

        await p.send_xt('mm', f'Revoked permission \'{permission.name}\' from user \'{target_penguin.username}\'', p.id)

    @_permissions.command('has', alias=['h'])
    @permissions.has_or_moderator('permissions.read')
    async def has_permission(self, p, target: str.lower, permission: Permission):
        if permission is None:
            return await p.send_xt('mm', 'Permission does not exist!', p.id)

        if target in p.server.penguins_by_username:
            target_penguin = p.server.penguins_by_username[target]
            has_permission = permissions.check_permission(target_penguin, permission.name)
            answer = 'has permission' if has_permission else 'does not have permission'
            await p.send_xt('mm', f'\'{target_penguin.username}\' {answer} \'{permission.name}\'', p.id)
