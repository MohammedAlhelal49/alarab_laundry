from odoo import Command

from .models.res_users import DEFAULT_PERMISSION_GROUP_XMLIDS


def assign_default_permission_groups(env):
    """
    Give all default custom permissions to existing internal users
    when the module is installed.
    """
    internal_group = env.ref('base.group_user')
    users = internal_group.users

    for xml_id in DEFAULT_PERMISSION_GROUP_XMLIDS:
        group = env.ref(xml_id, raise_if_not_found=False)

        if group:
            group.write({
                'users': [
                    Command.link(user.id)
                    for user in users
                ]
            })