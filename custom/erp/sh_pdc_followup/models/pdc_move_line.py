from odoo import models, fields


class PdcWizard(models.Model):
    """
    Adds pdc_followup_line_id to pdc.wizard.
    """
    _inherit = 'pdc.wizard'

    pdc_followup_line_id = fields.Many2one(
        comodel_name='pdc.followup.line',
        string='PDC Follow-up Level',
        copy=False,
    )
