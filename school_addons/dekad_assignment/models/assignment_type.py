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


class DeAssignmentType(models.Model):
    _name = 'de.assignment.type'
    _description = "Assignment Type"

    name = fields.Char(string="Name", required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per Assignment type"))
