# -*- coding: utf-8 -*-
# Part of DencCode. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    DencCode Inc
#    Copyright (C) 2009-TODAY DencCode Inc(<http://www.dekad.org>).
#
##############################################################################

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError


class LeaveType(models.Model):
    _name = 'de.leave.type'
    _description = "Manage students days off types"

    name = fields.Char(string="Name", required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per leave type"))
