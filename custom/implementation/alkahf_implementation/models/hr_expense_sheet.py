from odoo import models, fields, api


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    sequence = fields.Char(
        string="Code",
        readonly=True,
        copy=False,
        default='new'
    )

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'New') == 'New':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('hr.expense.sheet.seq') or 'new'
        return super().create(vals)

    def resequence_data(self):
        sheets = self.env['hr.expense.sheet'].search([], order='id asc')
        seq = self.env['ir.sequence']
        for sheet in sheets:
            sheet.sequence = seq.next_by_code('hr.expense.sheet.seq')


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    sequence = fields.Integer(default=10)

    _order = "sequence, id"

    account_move = fields.Many2one('account.move',
                                   string="Journal entry",
                                   compute="_compute_account_move"
                                   )


    @api.depends('total_amount', 'total_amount_currency')
    def _compute_price_unit(self):

        for expense in self:

            # keep manually entered value
            if expense._origin and expense.price_unit:
                continue

            if expense.state not in {'draft', 'reported'}:
                continue

            product_id = expense.product_id

            if expense._needs_product_price_computation():
                expense.price_unit = product_id._price_compute(
                    'standard_price',
                    uom=expense.product_uom_id,
                    company=expense.company_id,
                )[product_id.id]
            else:
                expense.price_unit = (
                    expense.company_currency_id.round(
                        expense.total_amount / expense.quantity
                    )
                    if expense.quantity else 0.
                )



    @api.depends('sheet_id.account_move_ids')
    def _compute_account_move(self):
        for rec in self:
            entry = self.env['account.move.line'].search([('expense_id', '=', rec.id)])
            print(entry)
            rec.account_move = \
                entry.mapped('move_id')[0] if entry else False

    def handle_expense_journals(self):
        for rec in self.search([]):
            entry = self.env['account.move.line'].search([('expense_id', '=', rec.id)])
            print(entry)
            rec.account_move = \
                entry.mapped('move_id')[0] if entry else False
