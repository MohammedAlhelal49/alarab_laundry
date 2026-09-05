from odoo import models, api, fields, exceptions, _


class DeFeeElement(models.Model):
    _name = "de.fee.element"
    _description = "Fees Element for fees terms lines"

    sequence = fields.Integer('Sequence')
    product_id = fields.Many2one('product.product',
                                 'Product(s)', required=True)
    value = fields.Float('Value (%)')
    fee_term_line_id = fields.Many2one('de.fee.term.line',
                                       string='Fee term line', ondelete="cascade")


class DeFeeTermLine(models.Model):
    _name = "de.fee.term.line"
    _description = "Fees Terms Line"

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    due_days = fields.Integer('Due Days')
    due_date = fields.Date('Due Date')
    value = fields.Float('Value (%)', required=True)

    fee_term_id = fields.Many2one('de.fee.term', 'Fees term', ondelete="cascade")
    fee_element_ids = fields.One2many("de.fee.element",
                                      "fee_term_line_id", "Fees Elements")

    @api.constrains('name', 'fee_term_id')
    def check_name(self):
        for rec in self:
            if rec.search_count([('name', '=', rec.name), ('fee_term_id', '=', rec.fee_term_id.id)]) > 1:
                raise exceptions.ValidationError(_(
                    f"Name must be unique per fees term line"))

    @api.constrains('value')
    def check_value(self):
        for rec in self:
            if rec.value <= 0.00:
                raise exceptions.ValidationError(_(
                    f"Fee term line value must be positive"))

    @api.constrains('fee_element_ids')
    def _check_term(self):
        for rec in self:
            if not rec.fee_element_ids:
                raise exceptions.ValidationError(_("Fees elements inside term must be Required!"))
            total = 0.0
            for line in rec.fee_element_ids:
                if line.value:
                    total += line.value
            if total != 100.0:
                raise exceptions.ValidationError(
                    _("Fees elements must be divided as such sum up in 100%"))


class DeFeeTerm(models.Model):
    _name = "de.fee.term"
    _inherit = "mail.thread"
    _description = "Fees Terms For Grade"

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    type = fields.Selection([('fixed_days', 'Fixed Fees of Days'),
                             ('fixed_date', 'Fixed Fees of Dates')],
                            string='Term Type', default='fixed_days', required=True)
    description = fields.Text('Description')
    fee_term_line_ids = fields.One2many('de.fee.term.line', 'fee_term_id', 'Terms')
    fee_term_line_count = fields.Integer('Term count', compute='compute_fee_term_line_count', readonly=True,
                                         store=True)

    @api.constrains('name')
    def check_name(self):
        for rec in self:
            if rec.search_count([('name', '=', rec.name)]) > 1:
                raise exceptions.ValidationError(_(
                    f"Name must be unique per fees terms"))

    @api.depends('fee_term_line_ids')
    def compute_fee_term_line_count(self):
        for rec in self:
            rec.fee_term_line_count = len(rec.fee_term_line_ids)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeFeeTerm, self).copy(default)

    @api.constrains('fee_term_line_ids')
    def _check_term(self):
        for rec in self:
            if not rec.fee_term_line_ids:
                raise exceptions.ValidationError(_("Fees Terms must be Required!"))
            total = 0.0
            for line in rec.fee_term_line_ids:
                if line.value:
                    total += line.value
            if total != 100.0:
                raise exceptions.ValidationError(
                    _("Fees terms must be divided as such sum up in 100%"))
