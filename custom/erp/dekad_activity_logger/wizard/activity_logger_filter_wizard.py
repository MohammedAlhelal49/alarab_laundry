from odoo import models, fields, api


class ActivityLoggerFilterWizard(models.TransientModel):
    _name = 'activity.logger.filter.wizard'
    _description = 'Activity Log Filter Wizard'

    user_ids = fields.Many2many(
        'res.users',
        string='Users'
    )

    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        default=lambda self: self.env.company
    )

    action_type_ids = fields.Many2many(
        'activity.logger.action.type',
        string='Action Types'
    )

    document_type_ids = fields.Many2many(
        'activity.logger.document.type',
        string='Document Types'
    )

    date_from = fields.Datetime(
        string='Date'
    )

    date_to = fields.Datetime(
        string='To Datetime'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        self._sync_filter_values()

        return res

    @api.model
    def _sync_filter_values(self):

        action_obj = self.env['activity.logger.action.type']
        document_obj = self.env['activity.logger.document.type']
        log_obj = self.env['activity.logger']

        # Action Types
        actions = {
            'create': 'Create',
            'write': 'Update',
            'unlink': 'Delete',
        }

        for code, display_name in actions.items():

            record = action_obj.search(
                [('code', '=', code)],
                limit=1
            )

            if not record:
                action_obj.create({
                    'name': display_name,
                    'code': code,
                })

        # Document Types
        document_types = log_obj.search([]).mapped(
            'document_type'
        )

        for document_type in set(document_types):

            if document_type and not document_obj.search(
                [('name', '=', document_type)],
                limit=1
            ):
                document_obj.create({
                    'name': document_type,
                })

    def action_show_logs(self):
        self.ensure_one()

        domain = [('log_source', '!=', 'system')]

        if self.user_ids:
            domain.append(
                ('user_id', 'in', self.user_ids.ids)
            )

        if self.company_ids:
            domain.append(
                ('company_id', 'in', self.company_ids.ids)
            )

        if self.action_type_ids:
            domain.append(
                (
                    'operation_type',
                    'in',
                    self.action_type_ids.mapped('code')
                )
            )

        if self.document_type_ids:
            domain.append(
                (
                    'document_type',
                    'in',
                    self.document_type_ids.mapped('name')
                )
            )

        if self.date_from:
            domain.append(
                ('create_date', '>=', self.date_from)
            )

        if self.date_to:
            domain.append(
                ('create_date', '<=', self.date_to)
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Filtered Activity Logs',
            'res_model': 'activity.logger',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': domain,
        }


class ActivityLoggerActionType(models.Model):
    _name = 'activity.logger.action.type'
    _description = 'Activity Logger Action Type'

    name = fields.Char(
        string='Display Name',
        required=True
    )

    code = fields.Char(
        string='Code',
        required=True
    )


class ActivityLoggerDocumentType(models.Model):
    _name = 'activity.logger.document.type'
    _description = 'Activity Logger Document Type'

    name = fields.Char(
        required=True
    )