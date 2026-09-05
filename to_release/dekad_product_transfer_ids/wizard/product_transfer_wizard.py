import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductTransferWizard(models.TransientModel):
    _name = 'product.transfer.wizard'
    _description = 'Product Transfer Wizard (ID-based)'

    state = fields.Selection([
        ('step1', 'Select Products'),
        ('step2', 'Review & Warnings'),
        ('step3', 'Confirm'),
        ('step4', 'Done'),
    ], default='step1')

    # ─── Step 1 ───────────────────────────────────────────────
    source_product_id = fields.Many2one(
        'product.product',
        string='Source Product (Wrong)',
        required=True,
    )
    target_product_id = fields.Many2one(
        'product.product',
        string='Target Product (Correct)',
        required=True,
    )
    archive_source = fields.Boolean(
        string='Archive Source Product after Transfer',
        default=True,
    )

    # ─── Step 2: counts ───────────────────────────────────────
    stock_move_done_count     = fields.Integer(readonly=True)
    stock_move_draft_count    = fields.Integer(readonly=True)
    stock_move_line_count     = fields.Integer(readonly=True)
    stock_quant_count         = fields.Integer(readonly=True)
    stock_lot_count           = fields.Integer(readonly=True)
    account_move_line_count   = fields.Integer(readonly=True)
    svl_count                 = fields.Integer(readonly=True)
    sale_line_count           = fields.Integer(readonly=True)
    purchase_line_count       = fields.Integer(readonly=True)
    pos_line_count            = fields.Integer(readonly=True)

    # ─── Warnings ─────────────────────────────────────────────
    warning_ids = fields.One2many(
        'product.transfer.warning', 'wizard_id',
        readonly=True,
    )
    has_blocking_warnings = fields.Boolean(readonly=True)

    # ─── Step 4 ───────────────────────────────────────────────
    result_log = fields.Text(readonly=True)

    # ══════════════════════════════════════════════════════════
    # STEP 1 → STEP 2
    # ══════════════════════════════════════════════════════════
    def action_analyze(self):
        self.ensure_one()
        self._validate_basic()
        self._compute_counts()
        self._compute_warnings()
        self.write({'state': 'step2'})
        return self._reload()

    def _validate_basic(self):
        if self.source_product_id == self.target_product_id:
            raise ValidationError(_('Source and Target products must be different.'))
        for model in ['stock.move', 'account.move.line', 'pos.order.line']:
            count = self.env[model].search_count([('product_id', '=', self.target_product_id.id)])
            if count:
                raise ValidationError(_(
                    'Target product "%s" is not empty — it has %d record(s) in %s.\n'
                    'Target product must have zero moves.'
                ) % (self.target_product_id.display_name, count, model))

    def _compute_counts(self):
        src = self.source_product_id.id
        self.stock_move_done_count = self.env['stock.move'].search_count([
            ('product_id', '=', src), ('state', '=', 'done'),
        ])
        self.stock_move_draft_count = self.env['stock.move'].search_count([
            ('product_id', '=', src), ('state', 'not in', ('done', 'cancel')),
        ])
        self.stock_move_line_count = self.env['stock.move.line'].search_count([
            ('product_id', '=', src),
        ])
        self.stock_quant_count = self.env['stock.quant'].search_count([
            ('product_id', '=', src),
        ])
        self.stock_lot_count = self.env['stock.lot'].search_count([
            ('product_id', '=', src),
        ])
        self.account_move_line_count = self.env['account.move.line'].search_count([
            ('product_id', '=', src),
        ])
        self.svl_count = self.env['stock.valuation.layer'].search_count([
            ('product_id', '=', src),
        ])
        self.sale_line_count = self.env['sale.order.line'].search_count([
            ('product_id', '=', src),
        ])
        self.purchase_line_count = self.env['purchase.order.line'].search_count([
            ('product_id', '=', src),
        ])
        self.pos_line_count = self.env['pos.order.line'].search_count([
            ('product_id', '=', src),
        ])

    def _compute_warnings(self):
        self.warning_ids.unlink()
        warnings = []
        src = self.source_product_id
        tgt = self.target_product_id
        has_blocking = False

        if src.uom_id != tgt.uom_id:
            warnings.append({
                'wizard_id': self.id, 'level': 'blocking',
                'message': _('UoM mismatch: Source "%s" vs Target "%s". Transfer cannot proceed.')
                           % (src.uom_id.name, tgt.uom_id.name),
            })
            has_blocking = True

        if src.type != tgt.type:
            warnings.append({
                'wizard_id': self.id, 'level': 'blocking',
                'message': _('Product type mismatch: Source "%s" vs Target "%s". Transfer cannot proceed.')
                           % (src.type, tgt.type),
            })
            has_blocking = True

        if src.tracking != tgt.tracking:
            warnings.append({
                'wizard_id': self.id, 'level': 'blocking',
                'message': _('Tracking mismatch: Source "%s" vs Target "%s". Transfer cannot proceed.')
                           % (src.tracking, tgt.tracking),
            })
            has_blocking = True

        # فحص تكرار stock.quant
        src_quants = self.env['stock.quant'].search([('product_id', '=', src.id)])
        for q in src_quants:
            conflict = self.env['stock.quant'].search([
                ('product_id', '=', tgt.id),
                ('location_id', '=', q.location_id.id),
                ('lot_id', '=', q.lot_id.id),
                ('package_id', '=', q.package_id.id),
                ('owner_id', '=', q.owner_id.id),
            ], limit=1)
            if conflict:
                warnings.append({
                    'wizard_id': self.id, 'level': 'blocking',
                    'message': _('Stock quant conflict in location "%s" — would cause duplicate key violation.')
                               % q.location_id.complete_name,
                })
                has_blocking = True
                break

        if src.categ_id != tgt.categ_id:
            warnings.append({
                'wizard_id': self.id, 'level': 'warning',
                'message': _('Category mismatch: Source "%s" vs Target "%s". Journal entries will keep original accounts.')
                           % (src.categ_id.complete_name, tgt.categ_id.complete_name),
            })

        if src.categ_id.property_cost_method != tgt.categ_id.property_cost_method:
            warnings.append({
                'wizard_id': self.id, 'level': 'warning',
                'message': _('Costing method mismatch: Source "%s" vs Target "%s". SVL chain may be affected.')
                           % (src.categ_id.property_cost_method, tgt.categ_id.property_cost_method),
            })

        if self.account_move_line_count:
            try:
                lock_date = self.env.company._get_user_fiscal_lock_date()
            except Exception:
                lock_date = False
            if lock_date:
                locked = self.env['account.move.line'].search_count([
                    ('product_id', '=', src.id),
                    ('date', '<=', lock_date),
                    ('move_id.state', '=', 'posted'),
                ])
                if locked:
                    warnings.append({
                        'wizard_id': self.id, 'level': 'warning',
                        'message': _('%d journal item(s) fall within a locked accounting period (before %s).')
                                   % (locked, lock_date),
                    })

        posted_invoices = self.env['account.move'].search_count([
            ('invoice_line_ids.product_id', '=', src.id),
            ('state', '=', 'posted'),
        ])
        if posted_invoices:
            warnings.append({
                'wizard_id': self.id, 'level': 'info',
                'message': _('%d posted invoice(s) found. Previously sent PDFs will still show the old product name.')
                           % posted_invoices,
            })

        self.env['product.transfer.warning'].create(warnings)
        self.has_blocking_warnings = has_blocking

    # ══════════════════════════════════════════════════════════
    # STEP 2 → STEP 3
    # ══════════════════════════════════════════════════════════
    def action_proceed(self):
        self.ensure_one()
        if self.has_blocking_warnings:
            raise UserError(_('Cannot proceed: blocking issues must be resolved first.'))
        self.write({'state': 'step3'})
        return self._reload()

    def action_back_to_step1(self):
        self.write({'state': 'step1'})
        return self._reload()

    def action_back_to_step2(self):
        self.write({'state': 'step2'})
        return self._reload()

    # ══════════════════════════════════════════════════════════
    # STEP 3 → STEP 4
    # ══════════════════════════════════════════════════════════
    def action_transfer(self):
        self.ensure_one()
        src_id = self.source_product_id.id
        tgt_id = self.target_product_id.id
        log_lines = []

        self.env.cr.execute("SAVEPOINT product_transfer_start")

        try:
            # 1. stock_lot أولاً — لأن stock_move_line._check_lot_product
            #    يتحقق من تطابق lot.product_id مع move_line.product_id
            count = self._sql_update('stock_lot', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Lots/Serial Numbers: %d updated' % count)

            # 2. stock_quant
            count = self._sql_update('stock_quant', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Stock Quants: %d updated' % count)

            # 3. stock_move_line — بعد lot لأن الـ constraint يتحقق من lot.product_id
            count = self._sql_update('stock_move_line', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Stock Move Lines: %d updated' % count)

            # 4. stock_move
            count = self._sql_update('stock_move', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Stock Moves: %d updated' % count)

            # 5. stock_scrap
            count = self._sql_update('stock_scrap', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Stock Scraps: %d updated' % count)

            # 6. stock_valuation_layer
            count = self._sql_update('stock_valuation_layer', 'product_id', src_id, tgt_id)
            log_lines.append('✅ Valuation Layers (SVL): %d updated' % count)

            # 7. account_move_line — product_id + name
            # _compute_name لا تحدّث الاسم إذا كان مختلفاً عن get_name(_origin)
            # لأن _origin يحتوي القيمة القديمة من الـ cache
            # الحل: نحدّث name مباشرة بـ SQL لكل سطر حسب نوع الجورنال
            count = self._sql_update('account_move_line', 'product_id', src_id, tgt_id)
            aml_ids = self.env['account.move.line'].search([
                ('product_id', '=', tgt_id),
                ('display_type', '=', 'product'),
            ])
            for aml in aml_ids:
                if not aml.product_id:
                    continue
                lang_code = aml.partner_id.lang or self.env.lang
                product = aml.product_id.with_context(lang=lang_code)
                values = [product.display_name]
                if aml.journal_id.type == 'sale' and product.description_sale:
                    values.append(product.description_sale)
                elif aml.journal_id.type == 'purchase' and product.description_purchase:
                    values.append(product.description_purchase)
                new_name = '\n'.join(values)
                self.env.cr.execute(
                    "UPDATE account_move_line SET name = %s WHERE id = %s",
                    (new_name, aml.id)
                )
            log_lines.append('✅ Journal Items: %d updated' % count)

            # 8. sale_order_line — product_id + إعادة حساب name
            count = self._sql_update('sale_order_line', 'product_id', src_id, tgt_id)
            sol_ids = self.env['sale.order.line'].search([
                ('product_id', '=', tgt_id),
                ('display_type', '=', False),
            ])
            for sol in sol_ids:
                new_name = sol._get_sale_order_line_multiline_description_sale()
                self.env.cr.execute(
                    "UPDATE sale_order_line SET name = %s WHERE id = %s",
                    (new_name, sol.id)
                )
            log_lines.append('✅ Sale Order Lines: %d updated' % count)

            # 9. purchase_order_line — product_id + إعادة حساب name
            # لا يوجد _compute_name — name محسوبة ضمن _compute_price_unit_and_date_planned_and_name
            # نستخدم _get_product_purchase_description مباشرة على كل سطر
            count = self._sql_update('purchase_order_line', 'product_id', src_id, tgt_id)
            pol_ids = self.env['purchase.order.line'].search([('product_id', '=', tgt_id)])
            for pol in pol_ids:
                if pol.product_id:
                    lang_code = pol.partner_id.lang or self.env.lang
                    product_lang = pol.product_id.with_context(
                        lang=lang_code,
                        seller_id=None,
                        partner_id=None,
                    )
                    new_name = pol._get_product_purchase_description(product_lang)
                    self.env.cr.execute(
                        "UPDATE purchase_order_line SET name = %s WHERE id = %s",
                        (new_name, pol.id)
                    )
            log_lines.append('✅ Purchase Order Lines: %d updated' % count)

            # 10. pos_order_line
            count = self._sql_update('pos_order_line', 'product_id', src_id, tgt_id)
            log_lines.append('✅ POS Order Lines: %d updated' % count)

            # 11. sync standard_price
            src_price = self.source_product_id.standard_price
            tgt_price = self.target_product_id.standard_price
            if src_price != tgt_price:
                self.env.cr.execute(
                    "UPDATE product_product SET standard_price = %s WHERE id = %s",
                    (src_price, tgt_id)
                )
                log_lines.append('✅ Standard price synced: %s → %s' % (tgt_price, src_price))

            # 12. Invalidate ORM cache
            for model in [
                'product.product', 'stock.move', 'stock.move.line',
                'stock.quant', 'stock.lot', 'stock.valuation.layer',
                'account.move.line',
            ]:
                self.env[model].invalidate_model()
            log_lines.append('✅ ORM cache invalidated')

            # 13. Archive source
            if self.archive_source:
                self.env.cr.execute(
                    "UPDATE product_product SET active = false WHERE id = %s", (src_id,)
                )
                self.env.cr.execute(
                    "UPDATE product_template SET active = false WHERE id = %s",
                    (self.source_product_id.product_tmpl_id.id,)
                )
                log_lines.append('✅ Source product archived')

            # 14. Chatter
            self.target_product_id.product_tmpl_id.message_post(
                body=_(
                    '<b>Product Transfer Completed</b><br/>'
                    'All moves transferred from: <b>%s</b> (id=%d)<br/>'
                    'Performed by: %s'
                ) % (self.source_product_id.display_name, src_id, self.env.user.name)
            )

            self.env.cr.execute("RELEASE SAVEPOINT product_transfer_start")
            _logger.info(
                'ProductTransfer (ID-based): [%s] → [%s] by %s',
                self.source_product_id.display_name,
                self.target_product_id.display_name,
                self.env.user.name,
            )

        except Exception as e:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT product_transfer_start")
            _logger.error('ProductTransfer failed: %s', str(e))
            raise UserError(_('Transfer failed and was fully rolled back.\nError: %s') % str(e))

        self.write({
            'result_log': '\n'.join(log_lines),
            'state': 'step4',
        })
        return self._reload()

    # ══════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════
    def _reload(self):
        """إرجاع action يعيد تحميل نفس الـ wizard — الطريقة الصحيحة في أودو 18 OWL"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _sql_update(self, table, column, src_id, tgt_id):
        self.env.cr.execute(
            "UPDATE %s SET %s = %%s WHERE %s = %%s" % (table, column, column),
            (tgt_id, src_id)
        )
        return self.env.cr.rowcount


class ProductTransferWarning(models.TransientModel):
    _name = 'product.transfer.warning'
    _description = 'Product Transfer Warning Line'

    wizard_id = fields.Many2one('product.transfer.wizard', ondelete='cascade')
    level = fields.Selection([
        ('info',     'Info'),
        ('warning',  'Warning'),
        ('blocking', 'Blocking'),
    ])
    message = fields.Text()
    level_icon = fields.Char(compute='_compute_icon')

    @api.depends('level')
    def _compute_icon(self):
        icons = {'info': 'ℹ️', 'warning': '⚠️', 'blocking': '🚫'}
        for rec in self:
            rec.level_icon = icons.get(rec.level, '')