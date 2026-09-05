from bisect import bisect_left
from collections import defaultdict
import contextlib
import itertools
import re
import json

from odoo import fields, models


class FarmType(models.Model):
    _name = "farm.type"
    _inherit = ['mail.thread']
    _description = "Farm type"

    name = fields.Char(string="Name", required=True)
    description = fields.Text('Description')

    _sql_constraints = [
        ('unique_name',
         'UNIQUE(name)',
         'Name of the Farm type should be unique')
    ]


class ResCompanyInherited(models.Model):
    _inherit = "res.company"

    farm_type_id = fields.Many2one('farm.type', 'Farm Type')
