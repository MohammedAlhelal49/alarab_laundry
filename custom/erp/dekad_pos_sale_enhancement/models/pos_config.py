from odoo import fields, models, api

from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_invoice_pdf_download = fields.Boolean(
        string="Auto-download Invoice PDF",
        help="If checked, invoice PDF will be downloaded after validation."
    )

    restrict_cashiers = fields.Boolean(
        string='Restrict Cashiers',
        help='If enabled, only selected employees will be available in POS.'
    )

    allowed_cashier_ids = fields.Many2many(
        'hr.employee',
        string='Allowed Cashiers',
        help='Only selected employees will be available as cashiers in POS.'
    )

    restrict_global_discount = fields.Boolean("Restrict Global Discount")
    max_global_discount = fields.Float("Maximum Global Discount (%)", default=0.0)

    enable_max_discount_limit = fields.Boolean(string="Limit Per-Line Discount")
    max_discount_percent = fields.Float(string="Max Allowed Discount (%)")

    hide_cash_control = fields.Boolean(string="Hide cache control")

    allowed_employee_user_ids = fields.Many2many(
        'hr.employee', 'allowed_employee_user_rel', compute="compute_allowed_employee_user_ids", store=True
    )

    enable_additional_charge = fields.Boolean(
        string="Enable Additional Charge",
        help="Allow applying an additional charge from the POS."
    )

    additional_charge_product_id = fields.Many2one(
        "product.product",
        string="Additional Charge Product",
        domain="[('is_additional_charge', '=', True)]",
        help="Product used when applying an additional charge."
    )

    additional_charge_percent = fields.Float(
        string="Default Additional Charge (%)",
        default=10,
    )
    stock_restriction_enabled = fields.Boolean(
        string="Restriction based on Stock quantity",
        default=False,
        help="Enable stock quantity restriction in POS",
    )
    stock_restriction_type = fields.Selection(
        selection=[
            ("alert", "Alert"),
            ("block", "Block"),
        ],
        string="Restriction Type",
        default=False,
    )

    @api.depends('allowed_cashier_ids', 'basic_employee_ids', 'advanced_employee_ids')
    def compute_allowed_employee_user_ids(self):
        for rec in self:
            rec.allowed_employee_user_ids = (
                        rec.allowed_cashier_ids | rec.basic_employee_ids | rec.advanced_employee_ids)

    # Extend POS Config to add a setting for allowing price override
    allow_price_override = fields.Boolean(
        string="Allow Price Out of Range",
        help="Allow setting prices in the POS that are below the minimum or above the maximum price limit."
    )

    # تفعيل/تعطيل الإشعارات
    notify_on_cash_difference = fields.Boolean(
        string='Notify on Cash Difference',
        default=False,
        help='Enable notifications when cash difference is detected on session close.'
    )

    # الحد الأدنى للفرق
    cash_difference_threshold = fields.Float(
        string='Minimum Difference Amount',
        default=5.0,
        help='Minimum cash difference amount to trigger notification. Set to 0 to notify on any difference.'
    )

    # الموظفين اللي يستلموا الإشعار
    cash_difference_notify_employee_ids = fields.Many2many(
        'hr.employee',
        'pos_config_cash_notify_employee_rel',
        'pos_config_id',
        'employee_id',
        string='Employees to Notify',
        help='Select employees who will receive email and activity notifications when cash difference is detected.'
    )

    price_control_allowed_employee_ids = fields.Many2many(
        'hr.employee',
        'pos_config_price_control_employee_rel',
        'config_id',
        'employee_id',
        string='Employees Allowed to Override Price Control',
    )

    use_strict_price_control_list = fields.Boolean(
        string='Restrict Price Control to Selected Employees Only',
        default=False,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Make sure the exception list travels to the frontend together with
        # the rest of the pos.config data, so the JS side can check it.
        params = super()._load_pos_data_fields(config_id)
        if not params:
            return params
        for field_name in ('price_control_allowed_employee_ids', 'use_strict_price_control_list'):
            if field_name not in params:
                params = params + [field_name]
        return params



    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['fields'].extend(['min_price', 'max_price'])
        return result

    # Ensure allow_price_override is also sent to POS
    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result["fields"].extend([
            "allow_price_override",
            "enable_additional_charge",
            "additional_charge_product_id",
            "additional_charge_percent",
        ])
        return result


    enable_whatsapp_template = fields.Boolean(
        string='Enable WhatsApp Template',
        help='Enable sending WhatsApp messages from this POS.'
    )

    whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Select WhatsApp Template',
        help='Select a default WhatsApp message template for this POS configuration.'
    )

    @api.onchange('enable_whatsapp_template')
    def _onchange_enable_whatsapp_template(self):
        if self.enable_whatsapp_template and not self.whatsapp_template_id:
            self.whatsapp_template_id = self.env.ref(
                'dekad_pos_sale_enhancement.whatsapp_invoice_template',
                raise_if_not_found=False
            )


    # Force-load the additional charge product into the POS session even if it
    # has no pos_categ_ids / doesn't match the config's category restriction,
    # so the Many2one relation on pos.config resolves correctly on the frontend.
    def _get_available_product_domain(self):
        domain = super()._get_available_product_domain()
        if self.enable_additional_charge and self.additional_charge_product_id:
            domain = ['|', ('id', '=', self.additional_charge_product_id.id)] + domain
        return domain


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_restrict_global_discount = fields.Boolean(
        string="Restrict Global Discount",
        related='pos_config_id.restrict_global_discount',
        readonly=False,
    )
    max_global_discount_percent = fields.Float(
        string="Maximum Global Discount (%)",
        related='pos_config_id.max_global_discount',
        readonly=False,
    )

    enable_max_discount_limit = fields.Boolean(related='pos_config_id.enable_max_discount_limit', readonly=False)
    max_discount_percent = fields.Float(related='pos_config_id.max_discount_percent', readonly=False)

    enable_additional_charge = fields.Boolean(
        related="pos_config_id.enable_additional_charge",
        readonly=False,
    )

    additional_charge_product_id = fields.Many2one(
        related="pos_config_id.additional_charge_product_id",
        readonly=False,
    )

    additional_charge_percent = fields.Float(
        related="pos_config_id.additional_charge_percent",
        readonly=False,
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])

        # If `allowed_cashier_ids` is defined, it restricts POS cashier list to those employees only.
        if config_id.restrict_cashiers:
            return [('id', 'in', config_id.allowed_cashier_ids.ids)]
        else:
            return config_id._employee_domain(config_id.current_user_id.id)
