# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import re
from odoo import api, fields, models,_
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools.translate import _



class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    name_ar = fields.Char(
        string='Company Name (Arabic)'
    )