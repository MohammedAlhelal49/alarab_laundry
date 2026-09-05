import json
from datetime import datetime, timedelta

from odoo import models, api, tools

RECENT_CREATES = {}
DELETED_MOVE_LINES = {}

class BaseModelLogger(models.AbstractModel):
    _inherit = 'base'

    IGNORED_FIELDS = {
        'id',
        '__last_update',
        'create_uid',
        'create_date',
        'write_uid',
        'write_date',

        'display_name',

        'image_1920',
        'image_1024',
        'image_512',
        'image_256',
        'image_128',

        'message_ids',
        'message_follower_ids',
        'message_partner_ids',
        'message_main_attachment_id',

        'activity_ids',
        'activity_state',
        'activity_type_id',
        'activity_user_id',
        'activity_date_deadline',
        'activity_exception_icon',
        'activity_exception_decoration',

        'website_message_ids',

        'needed_terms_dirty',
        'needed_terms',
        'quick_edit_mode',
        'quick_edit_total_amount',

        'amount_residual',
        'amount_residual_signed',

        'always_tax_exigible',

        '__domain',
    }


    @api.model
    @tools.ormcache()
    def _get_tracked_models(self):
        self.env.cr.execute(
            "SELECT model FROM ir_model WHERE is_activity_tracked = TRUE"
        )
        return set(row[0] for row in self.env.cr.fetchall())

    @api.model
    def _clear_tracked_models_cache(self):
        self.env.registry.clear_cache()

    def _log_custom_activity(
            self,
            operation,
            changes_dict,
            is_system_write=False,
            invoice_before=None,
    ):
        tracked_models = self._get_tracked_models()

        if self._name not in tracked_models:
            return self.env['activity.logger']

        if self._name == 'activity.logger':
            return self.env['activity.logger']

        invoice_before = invoice_before or {}

        model_id = self.env['ir.model']._get_id(
            self._name
        )

        created_loggers = self.env[
            'activity.logger'
        ]

        for record in self:

            changes = changes_dict.get(
                record.id,
                {}
            )

            technical_fields = {
                'write_uid',
                'write_date',
                '__last_update',
            }

            if is_system_write:
                log_source = 'system'

            elif operation in (
                    'create',
                    'unlink'
            ):
                log_source = 'user'

            elif any(
                    field not in technical_fields
                    for field in changes
            ):
                log_source = 'user'

            else:
                log_source = 'system'

            document_type = self._description

            if self._name == 'pdc.wizard':
                document_type = 'Cheque'

            elif self._name == 'hr.expense':
                document_type = 'Expense'

            elif self._name == 'hr.expense.sheet':
                document_type = 'Expense Report'

            elif self._name == 'sale.order':
                document_type = 'Sales Order'

            elif self._name == 'purchase.order':
                document_type = 'Purchase Order'

            elif self._name == 'stock.picking':
                document_type = 'Deliveries'

            elif self._name == 'account.move':

                document_type_map = {
                    'entry': 'Journal Entry',
                    'out_invoice': 'Customer Invoice',
                    'in_invoice': 'Vendor Bill',
                    'out_refund': 'Customer Credit Note',
                    'in_refund': 'Vendor Credit Note',
                    'out_receipt': 'Sales Receipt',
                    'in_receipt': 'Purchase Receipt',
                }

                document_type = document_type_map.get(
                    record.move_type,
                    'Journal Entry'
                )

            logger_vals = {
                'model_id': model_id,
                'record_id': record.id,
                'record_name': record.display_name,
                'company_id': self.env.company.id,
                'document_type': document_type,
                'operation_type': operation,
                'user_id': self.env.uid,
                'log_source': log_source,
                'changes_json': json.dumps(changes),
            }

            # Save deleted document lines
            if (
                    self._name in (
                    'account.move',
                    'sale.order',
                    'purchase.order',
                    'stock.picking',
            )
                    and operation == 'unlink'
            ):
                logger_vals['invoice_lines_json'] = json.dumps(
                    invoice_before.get(
                        record.id,
                        []
                    )
                )

            logger = self.env[
                'activity.logger'
            ].sudo().create(
                logger_vals
            )

            created_loggers |= logger

        return created_loggers



    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        tracked_models = self._get_tracked_models()

        if self._name not in tracked_models:
            return records

        for i, record in enumerate(records):

            RECENT_CREATES[(self._name, record.id)] = datetime.now()

            changes = {}

            for field_name, value in vals_list[i].items():

                if field_name in self.IGNORED_FIELDS:
                    continue

                field_label = record._get_field_label(
                    field_name
                )

                display_value = record._get_field_value(
                    record,
                    field_name
                )

                if display_value in (
                        False,
                        '',
                        None,
                        '(Empty)',
                        'False',
                        'None',
                        '[]',
                        '{}',
                ):
                    continue

                changes[field_label] = {
                    'old': '',
                    'new': display_value,
                }

            loggers = record._log_custom_activity(
                'create',
                {record.id: changes},
            )

            if self._name not in (
                    'account.move',
                    'sale.order',
                    'purchase.order',
                    'stock.picking',
            ):
                continue

            logger = loggers[:1]

            if not logger:
                continue

            snapshot = self._get_move_lines_snapshot(
                record
            )

            invoice_line_values = []

            for line in snapshot:
                invoice_line_values.append({
                    'logger_id': logger.id,
                    'snapshot_type': 'new',

                    'product': line.get('product', ''),
                    'account': line.get('account', ''),
                    'partner': line.get('partner', ''),
                    'label': line.get('label', ''),
                    'analytic': line.get('analytic', ''),

                    'analytic_distribution': line.get(
                        'analytic_distribution',
                        ''
                    ),

                    'location': line.get(
                        'location',
                        ''
                    ),

                    'location_dest': line.get(
                        'location_dest',
                        ''
                    ),

                    'date': line.get(
                        'date',
                        ''
                    ),

                    'date_deadline': line.get(
                        'date_deadline',
                        ''
                    ),

                    'packaging': line.get(
                        'packaging',
                        ''
                    ),

                    'unit_cost': line.get(
                        'unit_cost',
                        0
                    ),

                    'quantity': line.get('quantity', 0),
                    'uom': line.get('uom', ''),
                    'price': line.get('price', 0),

                    'discount': line.get(
                        'discount',
                        0
                    ),

                    'debit': line.get('debit', 0),
                    'credit': line.get('credit', 0),

                    'taxes': line.get('taxes', ''),
                    'amount': line.get('amount', 0),

                    'is_changed_quantity': False,
                    'is_changed_price': False,
                    'is_changed_amount': False,
                    'is_changed_product': False,
                    'is_changed_account': False,
                    'is_changed_analytic': False,
                    'is_changed_uom': False,
                    'is_changed_taxes': False,
                    'is_changed_discount': False,
                    'is_changed_analytic_distribution': False,

                    'is_changed_location': False,
                    'is_changed_location_dest': False,
                    'is_changed_date': False,
                    'is_changed_date_deadline': False,
                    'is_changed_packaging': False,
                    'is_changed_unit_cost': False,

                    'is_changed_partner': False,
                    'is_changed_label': False,
                    'is_changed_debit': False,
                    'is_changed_credit': False,
                })

            if invoice_line_values:
                self.env[
                    'activity.logger.invoice.line'
                ].sudo().create(
                    invoice_line_values
                )

        return records

    def write(self, vals):
        tracked_models = self._get_tracked_models()

        if self._name not in tracked_models:
            return super().write(vals)

        old_values = {
            rec.id: {
                field: self._get_field_value(
                    rec,
                    field
                )
                for field in vals.keys()
                if field not in self.IGNORED_FIELDS
            }
            for rec in self
        }

        invoice_before = {}

        if self._name in (
                'account.move',
                'sale.order',
                'purchase.order',
                'stock.picking',

        ):
            for rec in self:
                invoice_before[rec.id] = (
                    self._get_move_lines_snapshot(rec)
                )

        res = super().write(vals)

        invoice_after = {}

        if self._name in (
                'account.move',
                'sale.order',
                'purchase.order',
                'stock.picking',

        ):
            for rec in self:
                invoice_after[rec.id] = (
                    self._get_move_lines_snapshot(rec)
                )

        changes_dict = {}
        invoice_lines_changed = {}

        has_system_write = False

        for rec in self:

            if rec.create_date and rec.write_date:

                diff = abs(
                    (
                            rec.write_date -
                            rec.create_date
                    ).total_seconds()
                )

                if diff <= 3:
                    has_system_write = True

            changes = {}

            for field in vals.keys():

                if field in self.IGNORED_FIELDS:
                    continue

                old = old_values[rec.id].get(field)

                new = self._get_field_value(
                    rec,
                    field
                )

                if old != new:
                    field_label = rec._get_field_label(
                        field
                    )

                    changes[field_label] = {
                        'old': old,
                        'new': new,
                    }

            if changes:
                changes_dict[rec.id] = changes

        if self._name in (
                'account.move',
                'sale.order',
                'purchase.order',
                'stock.picking',

        ):

            for rec in self:

                before_lines = invoice_before.get(
                    rec.id,
                    []
                )

                after_lines = invoice_after.get(
                    rec.id,
                    []
                )

                invoice_lines_changed[rec.id] = (
                        before_lines != after_lines
                )

                if (
                        invoice_lines_changed[rec.id]
                        and rec.id not in changes_dict
                ):
                    changes_dict[rec.id] = {
                        'Invoice Lines': {
                            'old': 'Updated',
                            'new': 'Updated',
                        }
                    }

        if not changes_dict:
            return res

        loggers = self._log_custom_activity(
            'write',
            changes_dict,
            is_system_write=has_system_write,
        )

        if self._name not in (
                'account.move',
                'sale.order',
                'purchase.order',
                'stock.picking',

        ):
            return res


        logger_map = {
            logger.record_id: logger
            for logger in loggers
        }

        invoice_line_values = []

        for rec in self:

            logger = logger_map.get(rec.id)

            if not logger:
                continue

            before_lines = invoice_before.get(
                rec.id,
                []
            )

            after_lines = invoice_after.get(
                rec.id,
                []
            )

            old_map = {
                line['line_id']: line
                for line in before_lines
            }

            new_map = {
                line['line_id']: line
                for line in after_lines
            }

            all_ids = set(old_map.keys()) | set(new_map.keys())

            for line_id in all_ids:

                old_line = old_map.get(
                    line_id,
                    {}
                )

                new_line = new_map.get(
                    line_id,
                    {}
                )

                is_journal_entry = (
                        self._name == 'account.move'
                        and rec.move_type == 'entry'
                )
                # Default values for all change flags
                qty_changed = False
                price_changed = False
                amount_changed = False
                product_changed = False
                account_changed = False
                analytic_changed = False
                taxes_changed = False
                uom_changed = False
                discount_changed = False
                analytic_distribution_changed = False

                location_changed = False
                location_dest_changed = False
                date_changed = False
                date_deadline_changed = False
                packaging_changed = False
                unit_cost_changed = False

                partner_changed = False
                label_changed = False
                debit_changed = False
                credit_changed = False

                if is_journal_entry:

                    account_changed = (
                            old_line.get('account')
                            != new_line.get('account')
                    )

                    partner_changed = (
                            old_line.get('partner')
                            != new_line.get('partner')
                    )

                    label_changed = (
                            old_line.get('label')
                            != new_line.get('label')
                    )

                    analytic_changed = (
                            old_line.get('analytic')
                            != new_line.get('analytic')
                    )

                    taxes_changed = (
                            old_line.get('taxes')
                            != new_line.get('taxes')
                    )

                    debit_changed = (
                            old_line.get('debit')
                            != new_line.get('debit')
                    )

                    credit_changed = (
                            old_line.get('credit')
                            != new_line.get('credit')
                    )

                    if not any([
                        account_changed,
                        partner_changed,
                        label_changed,
                        analytic_changed,
                        taxes_changed,
                        debit_changed,
                        credit_changed,
                    ]):
                        continue

                else:

                    qty_changed = (
                            old_line.get('quantity')
                            != new_line.get('quantity')
                    )

                    price_changed = (
                            old_line.get('price')
                            != new_line.get('price')
                    )

                    amount_changed = (
                            old_line.get('amount')
                            != new_line.get('amount')
                    )

                    analytic_changed = (
                            old_line.get('analytic')
                            != new_line.get('analytic')
                    )

                    product_changed = (
                            old_line.get('product')
                            != new_line.get('product')
                    )

                    account_changed = (
                            old_line.get('account')
                            != new_line.get('account')
                    )

                    taxes_changed = (
                            old_line.get('taxes')
                            != new_line.get('taxes')
                    )

                    uom_changed = (
                            old_line.get('uom')
                            != new_line.get('uom')
                    )

                    discount_changed = (
                            old_line.get('discount')
                            != new_line.get('discount')
                    )

                    analytic_distribution_changed = (
                            old_line.get('analytic_distribution')
                            != new_line.get('analytic_distribution')
                    )
                    location_changed = (
                            old_line.get('location')
                            != new_line.get('location')
                    )

                    location_dest_changed = (
                            old_line.get('location_dest')
                            != new_line.get('location_dest')
                    )

                    date_changed = (
                            old_line.get('date')
                            != new_line.get('date')
                    )

                    date_deadline_changed = (
                            old_line.get('date_deadline')
                            != new_line.get('date_deadline')
                    )

                    packaging_changed = (
                            old_line.get('packaging')
                            != new_line.get('packaging')
                    )

                    unit_cost_changed = (
                            old_line.get('unit_cost')
                            != new_line.get('unit_cost')
                    )

                    if not any([
                        qty_changed,
                        price_changed,
                        amount_changed,
                        analytic_changed,
                        product_changed,
                        account_changed,
                        taxes_changed,
                        uom_changed,
                        discount_changed,
                        analytic_distribution_changed,
                        location_changed,
                        location_dest_changed,
                        date_changed,
                        date_deadline_changed,
                        packaging_changed,
                        unit_cost_changed,
                    ]):
                        continue

                invoice_line_values.append({
                    'logger_id': logger.id,
                    'snapshot_type': 'old',

                    'product': old_line.get('product', ''),
                    'account': old_line.get('account', ''),
                    'partner': old_line.get('partner', ''),
                    'label': old_line.get('label', ''),
                    'analytic': old_line.get('analytic', ''),

                    'quantity': old_line.get('quantity', 0),
                    'uom': old_line.get('uom', ''),
                    'price': old_line.get('price', 0),

                    'debit': old_line.get('debit', 0),
                    'credit': old_line.get('credit', 0),

                    'taxes': old_line.get('taxes', ''),
                    'amount': old_line.get('amount', 0),
                    'analytic_distribution': old_line.get(
                        'analytic_distribution',
                        ''
                    ),

                    'discount': old_line.get(
                        'discount',
                        0
                    ),
                    'location': old_line.get(
                        'location',
                        ''
                    ),

                    'location_dest': old_line.get(
                        'location_dest',
                        ''
                    ),

                    'date': old_line.get(
                        'date',
                        ''
                    ),

                    'date_deadline': old_line.get(
                        'date_deadline',
                        ''
                    ),

                    'packaging': old_line.get(
                        'packaging',
                        ''
                    ),

                    'unit_cost': old_line.get(
                        'unit_cost',
                        0
                    ),


                    'is_changed_quantity': qty_changed if not is_journal_entry else False,
                    'is_changed_price': price_changed if not is_journal_entry else False,
                    'is_changed_amount': amount_changed if not is_journal_entry else False,
                    'is_changed_product': product_changed if not is_journal_entry else False,
                    'is_changed_account': account_changed,
                    'is_changed_analytic': analytic_changed,
                    'is_changed_uom': uom_changed if not is_journal_entry else False,
                    'is_changed_taxes': taxes_changed,
                    'is_changed_discount':
                        discount_changed
                        if not is_journal_entry
                        else False,
                    'is_changed_location': location_changed,
                    'is_changed_location_dest': location_dest_changed,

                    'is_changed_date': date_changed,
                    'is_changed_date_deadline': date_deadline_changed,

                    'is_changed_packaging': packaging_changed,

                    'is_changed_unit_cost': unit_cost_changed,
                    'is_changed_analytic_distribution':
                        analytic_distribution_changed
                        if not is_journal_entry
                        else False,

                    'is_changed_partner': partner_changed if is_journal_entry else False,
                    'is_changed_label': label_changed if is_journal_entry else False,
                    'is_changed_debit': debit_changed if is_journal_entry else False,
                    'is_changed_credit': credit_changed if is_journal_entry else False,
                })

                invoice_line_values.append({
                    'logger_id': logger.id,
                    'snapshot_type': 'new',

                    'product': new_line.get('product', ''),
                    'account': new_line.get('account', ''),
                    'partner': new_line.get('partner', ''),
                    'label': new_line.get('label', ''),
                    'analytic': new_line.get('analytic', ''),

                    'quantity': new_line.get('quantity', 0),
                    'uom': new_line.get('uom', ''),
                    'price': new_line.get('price', 0),

                    'debit': new_line.get('debit', 0),
                    'credit': new_line.get('credit', 0),

                    'taxes': new_line.get('taxes', ''),
                    'amount': new_line.get('amount', 0),
                    'analytic_distribution': new_line.get(
                        'analytic_distribution',
                        ''
                    ),

                    'discount': new_line.get(
                        'discount',
                        0
                    ),
                    'location': new_line.get(
                        'location',
                        ''
                    ),

                    'location_dest': new_line.get(
                        'location_dest',
                        ''
                    ),

                    'date': new_line.get(
                        'date',
                        ''
                    ),

                    'date_deadline': new_line.get(
                        'date_deadline',
                        ''
                    ),

                    'packaging': new_line.get(
                        'packaging',
                        ''
                    ),

                    'unit_cost': new_line.get(
                        'unit_cost',
                        0
                    ),


                    'is_changed_quantity': qty_changed if not is_journal_entry else False,
                    'is_changed_price': price_changed if not is_journal_entry else False,
                    'is_changed_amount': amount_changed if not is_journal_entry else False,
                    'is_changed_product': product_changed if not is_journal_entry else False,
                    'is_changed_account': account_changed,
                    'is_changed_analytic': analytic_changed,
                    'is_changed_uom': uom_changed if not is_journal_entry else False,
                    'is_changed_taxes': taxes_changed,
                    'is_changed_discount':
                        discount_changed
                        if not is_journal_entry
                        else False,
                    'is_changed_location': location_changed,
                    'is_changed_location_dest': location_dest_changed,

                    'is_changed_date': date_changed,
                    'is_changed_date_deadline': date_deadline_changed,

                    'is_changed_packaging': packaging_changed,

                    'is_changed_unit_cost': unit_cost_changed,

                    'is_changed_analytic_distribution':
                        analytic_distribution_changed
                        if not is_journal_entry
                        else False,

                    'is_changed_partner': partner_changed if is_journal_entry else False,
                    'is_changed_label': label_changed if is_journal_entry else False,
                    'is_changed_debit': debit_changed if is_journal_entry else False,
                    'is_changed_credit': credit_changed if is_journal_entry else False,
                })

        if invoice_line_values:
            self.env[
                'activity.logger.invoice.line'
            ].sudo().create(
                invoice_line_values
            )

        return res

    def unlink(self):

        # Capture Account Move lines BEFORE Odoo deletes them
        if self._name == 'account.move.line':

            for line in self:

                if not line.move_id:
                    continue

                move_id = line.move_id.id

                if move_id not in DELETED_MOVE_LINES:
                    DELETED_MOVE_LINES[move_id] = []

                if line.move_id.move_type == 'entry':

                    DELETED_MOVE_LINES[move_id].append({
                        'line_id': line.id,

                        'account': self._safe_display_name(
                            line.account_id
                        ),
                        'partner': self._safe_display_name(
                            line.partner_id
                        ),
                        'label': line.name,
                        'analytic': self._get_analytic_names(line),

                        'taxes': self._safe_display_names(
                            line.tax_ids
                        ),

                        'debit': line.debit,
                        'credit': line.credit,
                    })

                else:

                    if not line.product_id:
                        continue

                    DELETED_MOVE_LINES[move_id].append({
                        'line_id': line.id,

                        'product': self._safe_display_name(line.product_id),
                        'account': self._safe_display_name(line.account_id),
                        'analytic': self._get_analytic_names(line),

                        'quantity': line.quantity,
                        'uom': self._safe_display_name(line.product_uom_id),
                        'price': line.price_unit,

                        'taxes': self._safe_display_names(
                            line.tax_ids
                        ),

                        'discount': line.discount,
                        'amount': line.price_subtotal,
                    })

            return super().unlink()

        # Capture Stock Move lines BEFORE Odoo deletes them
        if self._name == 'stock.move':

            for line in self:

                if not line.picking_id:
                    continue

                picking_id = line.picking_id.id

                if picking_id not in DELETED_MOVE_LINES:
                    DELETED_MOVE_LINES[picking_id] = []

                DELETED_MOVE_LINES[picking_id].append({
                    'line_id': line.id,

                    'product': self._safe_display_name(
                        line.product_id
                    ),

                    'location': self._safe_display_name(
                        line.location_id
                    ),

                    'location_dest': self._safe_display_name(
                        line.location_dest_id
                    ),

                    'date': (
                        str(line.date)
                        if line.date
                        else ''
                    ),

                    'date_deadline': (
                        str(line.date_deadline)
                        if line.date_deadline
                        else ''
                    ),

                    'packaging': self._safe_display_name(
                        line.product_packaging_id
                    ),

                    'analytic': (
                        self._safe_display_name(
                            line.analytic_account_id
                        )
                        if hasattr(line, 'analytic_account_id')
                        else ''
                    ),

                    'quantity': line.product_uom_qty,

                    'uom': self._safe_display_name(
                        line.product_uom
                    ),

                    'unit_cost': (
                        line.unit_cost
                        if hasattr(line, 'unit_cost')
                        else 0
                    ),

                    'amount': (
                        line.cost_amount
                        if hasattr(line, 'cost_amount')
                        else 0
                    ),
                })

            return super().unlink()

        tracked_models = self._get_tracked_models()

        if self._name not in tracked_models:
            return super().unlink()

        changes_dict = {}
        invoice_before = {}

        for rec in self:

            if self._name == 'account.move':

                invoice_before[rec.id] = (
                    DELETED_MOVE_LINES.get(
                        rec.id,
                        []
                    )
                )

            elif self._name == 'stock.picking':

                invoice_before[rec.id] = (
                    DELETED_MOVE_LINES.get(
                        rec.id,
                        []
                    )
                )

            elif self._name in (
                    'sale.order',
                    'purchase.order',
            ):

                invoice_before[rec.id] = (
                    self._get_move_lines_snapshot(rec)
                )

            changes = {}

            for field_name, field in rec._fields.items():

                if field_name in self.IGNORED_FIELDS:
                    continue

                if not field.store:
                    continue

                value = self._get_field_value(
                    rec,
                    field_name
                )

                if value in (
                        '(Empty)',
                        '',
                        False,
                        None,
                ):
                    continue

                changes[
                    self._get_field_label(field_name)
                ] = {
                    'old': value,
                    'new': 'Deleted',
                }

            changes_dict[rec.id] = changes

        self._log_custom_activity(
            'unlink',
            changes_dict,
            invoice_before=invoice_before,
        )

        if self._name in (
                'account.move',
                'stock.picking',
        ):

            for rec in self:
                DELETED_MOVE_LINES.pop(
                    rec.id,
                    None
                )

        return super().unlink()

    def _get_field_label(self, field_name):
        field = self._fields.get(field_name)

        if field:
            return field.string

        return field_name.replace('_', ' ').title()

    def _get_field_value(self, record, field_name):
        field = record._fields.get(field_name)

        if not field:
            return str(record[field_name])

        value = record[field_name]

        # Empty values
        if value in (False, None):
            return '(Empty)'

        # Many2one
        if field.type == 'many2one':
            return self._safe_display_name(
                value,
                empty_value='(Deleted)',
            )

        # Many2many
        if field.type == 'many2many':
            return self._safe_display_names(
                value,
                empty_value='(Empty)',
            )

        # One2many
        if field.type == 'one2many':
            return self._safe_display_names(
                value,
                empty_value='(Empty)',
            )

        # Selection
        if field.type == 'selection':
            try:
                selection = field.selection

                if callable(selection):
                    selection = selection(record)

                selection_dict = dict(selection)

                return selection_dict.get(
                    value,
                    str(value)
                )

            except Exception:
                try:
                    return field.convert_to_export(
                        value,
                        record
                    )
                except Exception:
                    return str(value)

        # Boolean
        if field.type == 'boolean':
            return 'Yes' if value else 'No'

        # Date
        if field.type == 'date':
            return (
                value.strftime('%d/%m/%Y')
                if value
                else '(Empty)'
            )

        # Datetime
        if field.type == 'datetime':
            return (
                value.strftime('%d/%m/%Y %H:%M:%S')
                if value
                else '(Empty)'
            )

        # Monetary / Float
        if field.type in ('float', 'monetary'):
            return str(value)

        # Default
        return str(value)

    def _get_move_lines_snapshot(self, move):
        lines = []

        # ==========================================================
        # Journal Entry
        # ==========================================================
        if (
                move._name == 'account.move'
                and move.move_type == 'entry'
        ):
            move_lines = move.line_ids.filtered(
                lambda line: line.display_type not in (
                    'line_section',
                    'line_note',
                )
            )

            for line in move_lines:
                lines.append({
                    'line_id': line.id,

                    'account': self._safe_display_name(
                        line.account_id
                    ),

                    'partner': self._safe_display_name(
                        line.partner_id
                    ),

                    'label': line.name or '',

                    'analytic': self._get_analytic_names(
                        line
                    ),

                    'taxes': self._safe_display_names(
                        line.tax_ids
                    ),

                    'debit': line.debit,
                    'credit': line.credit,

                    'is_journal_item': True,
                })

        # ==========================================================
        # Customer Invoice / Vendor Bill / Credit Note
        # ==========================================================
        elif move._name == 'account.move':

            for line in move.invoice_line_ids:

                if not line.product_id:
                    continue

                lines.append({
                    'line_id': line.id,

                    'product': self._safe_display_name(
                        line.product_id
                    ),

                    'account': self._safe_display_name(
                        line.account_id
                    ),

                    'analytic': self._get_analytic_names(
                        line
                    ),

                    'analytic_distribution':
                        self._get_analytic_distribution_names(
                            line
                        ),

                    'quantity': line.quantity,

                    'uom': self._safe_display_name(
                        line.product_uom_id
                    ),

                    'price': line.price_unit,

                    'taxes': self._safe_display_names(
                        line.tax_ids
                    ),

                    'discount': line.discount,
                    'amount': line.price_subtotal,

                    'is_journal_item': False,
                })

        # ==========================================================
        # Sale Order
        # ==========================================================
        elif move._name == 'sale.order':

            for line in move.order_line:

                if not line.product_id:
                    continue

                lines.append({
                    'line_id': line.id,

                    'product': self._safe_display_name(
                        line.product_id
                    ),

                    'analytic_distribution':
                        self._get_analytic_distribution_names(
                            line
                        ),

                    'quantity': line.product_uom_qty,

                    'uom': self._safe_display_name(
                        line.product_uom
                    ),

                    'price': line.price_unit,

                    'taxes': self._safe_display_names(
                        line.tax_id
                    ),

                    'discount': line.discount,
                    'amount': line.price_subtotal,

                    'is_journal_item': False,
                })

        # ==========================================================
        # Purchase Order
        # ==========================================================
        elif move._name == 'purchase.order':

            for line in move.order_line:

                if not line.product_id:
                    continue

                lines.append({
                    'line_id': line.id,

                    'product': self._safe_display_name(
                        line.product_id
                    ),

                    'analytic_distribution':
                        self._get_analytic_distribution_names(
                            line
                        ),

                    'quantity': line.product_qty,

                    'uom': self._safe_display_name(
                        line.product_uom
                    ),

                    'price': line.price_unit,

                    'taxes': self._safe_display_names(
                        line.taxes_id
                    ),

                    'discount': getattr(
                        line,
                        'discount',
                        0
                    ),

                    'amount': line.price_subtotal,

                    'is_journal_item': False,
                })

        # ==========================================================
        # Delivery / Stock Picking
        # ==========================================================
        elif move._name == 'stock.picking':

            for line in move.move_ids_without_package:

                if not line.product_id:
                    continue

                analytic_name = ''

                if hasattr(line, 'analytic_account_id'):
                    analytic_name = self._safe_display_name(
                        line.analytic_account_id
                    )

                lines.append({
                    'line_id': line.id,

                    'product': self._safe_display_name(
                        line.product_id
                    ),

                    'location': self._safe_display_name(
                        line.location_id
                    ),

                    'location_dest': self._safe_display_name(
                        line.location_dest_id
                    ),

                    'date': (
                        str(line.date)
                        if line.date
                        else ''
                    ),

                    'date_deadline': (
                        str(line.date_deadline)
                        if line.date_deadline
                        else ''
                    ),

                    'packaging': self._safe_display_name(
                        line.product_packaging_id
                    ),

                    'analytic': analytic_name,

                    'quantity': line.product_uom_qty,

                    'uom': self._safe_display_name(
                        line.product_uom
                    ),

                    'unit_cost': (
                        line.unit_cost
                        if hasattr(line, 'unit_cost')
                        else 0
                    ),

                    'amount': (
                        line.cost_amount
                        if hasattr(line, 'cost_amount')
                        else 0
                    ),

                    'is_journal_item': False,
                })

        return lines

    def _get_analytic_names(self, line):
        """
        Return analytic account names from analytic_distribution.

        Important:
        analytic_distribution stores analytic IDs inside JSON.
        The referenced analytic account may already have been deleted,
        so .exists() must be used before reading display_name.
        """
        analytic_ids = []

        for key in (
                line.analytic_distribution or {}
        ).keys():

            for analytic_id in str(key).split(','):

                analytic_id = analytic_id.strip()

                if analytic_id.isdigit():
                    analytic_ids.append(
                        int(analytic_id)
                    )

        if not analytic_ids:
            return ''

        analytic_accounts = self.env[
            'account.analytic.account'
        ].browse(
            analytic_ids
        ).exists()

        if not analytic_accounts:
            return ''

        return ', '.join(
            analytic_accounts.mapped(
                'display_name'
            )
        )

    def _get_analytic_distribution_names(self, line):
        """
        Convert analytic_distribution into readable names.

        Example:
            {'10': 100.0}

        becomes:
            Project A (100.0%)

        Deleted analytic accounts are ignored safely.
        """
        distribution = (
                line.analytic_distribution or {}
        )

        result = []

        for analytic_key, percentage in distribution.items():

            analytic_ids = []

            for analytic_id in str(
                    analytic_key
            ).split(','):

                analytic_id = (
                    analytic_id.strip()
                )

                if analytic_id.isdigit():
                    analytic_ids.append(
                        int(analytic_id)
                    )

            if not analytic_ids:
                continue

            analytic_accounts = self.env[
                'account.analytic.account'
            ].browse(
                analytic_ids
            ).exists()

            if not analytic_accounts:
                continue

            names = analytic_accounts.mapped(
                'display_name'
            )

            if names:
                result.append(
                    f"{', '.join(names)} "
                    f"({percentage}%)"
                )

        return ', '.join(result)


    def _safe_display_name(self, record, empty_value=''):

        if not record:
            return empty_value

        existing_record = record.exists()

        if not existing_record:
            return empty_value

        return existing_record.display_name

    def _safe_display_names(self, records, empty_value=''):
        """
        Safely get comma-separated display names from a recordset.

        Useful for Many2many / One2many fields.
        """
        if not records:
            return empty_value

        existing_records = records.exists()

        if not existing_records:
            return empty_value

        return ', '.join(
            existing_records.mapped('display_name')
        )