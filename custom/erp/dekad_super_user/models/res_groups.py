# -*- coding: utf-8 -*-
###############################################################################
#
#    SyncCode Inc
#    Copyright (C) 2009-TODAY SyncCode Inc(<http://www.synccode.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


# < div
#
#
# class ="alert alert-warning" role="alert" colspan="2" attrs="{'invisible': [('user_group_warning', '=', False)]}" >
#
# < label
# for ="user_group_warning" string="Access Rights Mismatch" class ="text text-warning fw-bold" / >
# < field
# name = "user_group_warning" / >
# < / div >

import binascii
import contextlib
import collections
import datetime
import hmac
import ipaddress
import itertools
import json
import logging
import os
import time
from collections import defaultdict
from functools import wraps
from hashlib import sha256
from itertools import chain, repeat
from markupsafe import Markup

import pytz
from lxml import etree
from lxml.builder import E
from passlib.context import CryptContext as _CryptContext

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request, DEFAULT_LANG
from odoo.osv import expression
from odoo.tools import is_html_empty, partition, frozendict, lazy_property, SQL, SetDefinitions
from odoo.tools.misc import OrderedSet

_logger = logging.getLogger(__name__)

# def name_boolean_group(id):
#     return 'in_group_' + str(id)
#
#
# def name_selection_groups(ids):
#     return 'sel_groups_' + '_'.join(str(it) for it in sorted(ids))
#
#
# def is_boolean_group(name):
#     return name.startswith('in_group_')
#
#
# def is_selection_groups(name):
#     return name.startswith('sel_groups_')
#
#
# def is_reified_group(name):
#     return is_boolean_group(name) or is_selection_groups(name)
#
#
# def get_boolean_group(name):
#     return int(name[9:])
#
#
# def get_selection_groups(name):
#     return [int(v) for v in name[11:].split('_')]

def name_boolean_group(id):
    return 'in_group_' + str(id)


def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in sorted(ids))


def is_boolean_group(name):
    return name.startswith('in_group_')


def is_selection_groups(name):
    return name.startswith('sel_groups_')


def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)


def get_boolean_group(name):
    return int(name[9:])


def get_selection_groups(name):
    return [int(v) for v in name[11:].split('_')]
class ResGroups(models.Model):
    _inherit = "res.groups"



    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        # remove the language to avoid translations, it will be handled at the view level
        self = self.with_context(lang=None)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if not (view and view._name == 'ir.ui.view'):
            return

        if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
            # use a dummy view during install/upgrade/uninstall
            xml = E.field(name="groups_id", position="after")

        else:
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml0, xml1, xml2, xml3, xml4 = [], [], [], [], []
            xml_by_category = {}
            xml1.append(E.separator(string='User Type', colspan="2", groups='base.group_no_one'))

            user_type_field_name = ''
            user_type_readonly = str({})
            sorted_tuples = sorted(self.get_groups_by_application(),
                                   key=lambda t: t[0].xml_id != 'base.module_category_user_type')

            invisible_information = "All fields linked to groups must be present in the view due to the overwrite of create and write. The implied groups are calculated using this values."

            for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
                attrs = {}
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                if app.xml_id in self._get_hidden_extra_categories():
                    attrs['groups'] = 'base.group_no_one'
                # User type (employee, portal or public) is a separated group. This is the only 'selection'
                # group of res.groups without implied groups (with each other).
                if app.xml_id == 'base.module_category_user_type':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    # test_reified_groups, put the user category type in invisible
                    # as it's used in domain of attrs of other fields,
                    # and the normal user category type field node is wrapped in a `groups="base.no_one"`,
                    # and is therefore removed when not in debug mode.
                    xml0.append(E.field(name=field_name, invisible="True", on_change="1"))
                    xml0.append(etree.Comment(invisible_information))
                    user_type_field_name = field_name
                    user_type_readonly = f'{user_type_field_name} != {group_employee.id}'
                    attrs['widget'] = 'radio'
                    # Trigger the on_change of this "virtual field"
                    attrs['on_change'] = '1'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    attrs['readonly'] = user_type_readonly
                    attrs['on_change'] = '1'
                    if category_name not in xml_by_category:
                        xml_by_category[category_name] = []
                        xml_by_category[category_name].append(E.newline())
                    xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                    xml_by_category[category_name].append(E.newline())
                    # add duplicate invisible field so default values are saved on create
                    if attrs.get('groups') == 'base.group_no_one':
                        xml0.append(
                            E.field(name=field_name, **dict(attrs, invisible="True", groups='!base.group_no_one')))
                        xml0.append(etree.Comment(invisible_information))

                else:


                    # application separator with boolean fields
                    app_name = app.name or 'Other'
                    if app_name in ("Accounting Additional Permissions" , "Inventory Additional Permissions" , "Purchase Additional Permissions" , "Sales Additional Permissions") :
                        print(1 == 1)
                    else:
                        attrs['groups'] = 'base.group_no_one'
                    xml4.append(E.separator(string=app_name, **attrs))
                    left_group, right_group = [], []
                    attrs['readonly'] = user_type_readonly
                    # we can't use enumerate, as we sometime skip groups
                    group_count = 0
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        dest_group = left_group if group_count % 2 == 0 else right_group
                        if g in (group_no_one, self.env.ref('dekad_super_user.group_de_support')):
                            # make the group_no_one invisible in the form view
                            dest_group.append(E.field(name=field_name, invisible="True", **attrs))
                            dest_group.append(etree.Comment(invisible_information))
                        else:
                            dest_group.append(E.field(name=field_name, **attrs))
                        # add duplicate invisible field so default values are saved on create
                        xml0.append(
                            E.field(name=field_name, **dict(attrs, invisible="True", groups='!base.group_no_one')))
                        xml0.append(etree.Comment(invisible_information))
                        group_count += 1
                    xml4.append(E.group(*left_group))
                    xml4.append(E.group(*right_group))

            xml4.append({'class': "o_label_nowrap"})
            user_type_invisible = f'{user_type_field_name} != {group_employee.id}' if user_type_field_name else None

            for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
                master_category_name = xml_cat[1]
                xml3.append(E.group(*(xml_by_category[xml_cat]), string=master_category_name))

            field_name = 'user_group_warning'
            user_group_warning_xml = E.div({
                'class': "alert alert-warning",
                'role': "alert",
                'colspan': "2",
                'invisible': f'not {field_name}',
            })
            user_group_warning_xml.append(E.label({
                'for': field_name,
                'string': "Access Rights Mismatch",
                'class': "text text-warning fw-bold",
            }))
            user_group_warning_xml.append(E.field(name=field_name))
            xml2.append(user_group_warning_xml)

            xml = E.field(
                *(xml0),
                E.group(*(xml1), groups="base.group_no_one"),
                E.group(*(xml2), invisible=user_type_invisible),
                E.group(*(xml3), invisible=user_type_invisible),
                E.group(*(xml4), invisible=user_type_invisible), name="groups_id",
                position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))

        # serialize and update the view
        xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")
        if xml_content != view.arch:  # avoid useless xml validation if no change
            new_context = dict(view._context)
            new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})
