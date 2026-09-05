from odoo import models, api, _, fields
from odoo.exceptions import ValidationError
from odoo.tools import sql
from lxml import etree

class BaseDynamicRequired(models.AbstractModel):
    _inherit = 'base'

    dynamic_duplicate_warning = fields.Html(
        string='Duplicate Warning',
        compute='_compute_dynamic_duplicate_warning',
        sanitize=False
    )

    def _get_dynamic_configs(self, domain):
        if 'required.field.config' not in self.env:
            return self.env['ir.model'].browse()

        Config = self.env['required.field.config']

        if not sql.table_exists(self.env.cr, Config._table):
            return Config.browse()

        return Config.sudo().search(domain)


    # =====================================================
    # REQUIRED VALIDATION
    # =====================================================

    def _validate_dynamic_required(self, vals=None):

        configs = self._get_dynamic_configs([
            ('required', '=', True),
            ('model_id.model', '=', self._name),
        ])

        if not configs:
            return

        product_line_fields = {
            'analytic_distribution',
            'discount',
            'quantity',
            'price_unit',
            'product_id',
        }

        for record in self:

            # For account.move.line, editing any of the line's core
            # "content" fields (quantity, price, product, etc.) is a real
            # content edit - saving that line should re-validate ALL
            # configured required fields on it, not just whichever field
            # happened to change. Without this, changing quantity while
            # analytic_distribution stays empty would silently save.
            #
            # An unrelated write that touches none of these content
            # fields (e.g. reconciliation, payment status, other system
            # bookkeeping) still falls through to the narrow "only check
            # the field actually in vals" behaviour below, so it won't
            # get blocked by a pre-existing empty value it never touched.
            line_content_edit = (
                vals is not None
                and record._name == 'account.move.line'
                and bool(set(vals) & product_line_fields)
            )

            for config in configs:

                field_name = config.field_id.name

                if field_name not in record._fields:
                    continue

                if (
                    vals is not None
                    and field_name not in vals
                    and not line_content_edit
                ):
                    continue

                # Skip automatically generated invoice lines for fields
                # that only make sense on product lines.
                if (
                        record._name == 'account.move.line'
                        and field_name in product_line_fields
                        and record.display_type != 'product'
                ):
                    continue

                value = record[field_name]

                if hasattr(value, '__len__') and not isinstance(value, str):
                    is_empty = len(value) == 0
                else:
                    is_empty = not value

                if is_empty:
                    raise ValidationError(_(
                        "Field '%s' is required."
                    ) % config.field_id.field_description)

    # =====================================================
    # PREVENT DUPLICATES
    # =====================================================

    def _validate_prevent_duplicates(self, vals=None):

        configs = self._get_dynamic_configs([
            ('prevent_duplicate', '=', True),
            ('model_id.model', '=', self._name),
        ])

        if not configs:
            return

        for record in self:

            for config in configs:


                field_name = config.field_id.name

                if field_name not in record._fields:
                    continue

                if vals is not None and field_name not in vals:
                    continue

                value = record[field_name]

                if not value:
                    continue

                # many2one support
                if hasattr(value, 'id'):
                    search_value = value.id
                else:
                    search_value = value

                domain = [
                    (field_name, '=', search_value),
                    ('id', '!=', record.id),
                ]

                duplicate = self.env[record._name].search(
                    domain,
                    limit=1
                )

                if duplicate:

                    company_name = ''

                    if (
                        'company_id' in duplicate._fields
                        and duplicate.company_id
                    ):
                        company_name = duplicate.company_id.display_name

                    raise ValidationError(_(
                        "Duplicate detected.\n\n"
                        "Field: %(field)s\n"
                        "Value: %(value)s\n"
                        "Duplicate Record: %(record)s\n"
                        "Company: %(company)s"
                    ) % {
                        'field': config.field_id.field_description,
                        'value': value.display_name if hasattr(value, 'display_name') else value,
                        'record': duplicate.display_name,
                        'company': company_name or _('No Company'),
                    })

    # =====================================================
    # DUPLICATE WARNING
    # =====================================================

    def _compute_dynamic_duplicate_warning(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )

        configs = self._get_dynamic_configs([
            ('duplicate_warning', '=', True),
            ('model_id.model', '=', self._name),
        ])

        for record in self:
            warnings = []

            for config in configs:
                field_name = config.field_id.name

                if field_name not in record._fields:
                    continue

                value = record[field_name]

                if not value:
                    continue

                if hasattr(value, 'id'):
                    search_value = value.id
                    display_value = value.display_name
                else:
                    search_value = value
                    display_value = value

                domain = [
                    (field_name, '=', search_value),
                ]

                if isinstance(record.id, int):
                    domain.append(('id', '!=', record.id))

                duplicate = self.env[record._name].search(
                    domain,
                    limit=1,
                )

                if not duplicate:
                    continue

                company_name = ''

                if (
                        'company_id' in duplicate._fields
                        and duplicate.company_id
                ):
                    company_name = duplicate.company_id.display_name

                record_url = (
                    f"{base_url}/web#"
                    f"id={duplicate.id}"
                    f"&model={duplicate._name}"
                    f"&view_type=form"
                )

                warnings.append(f"""
                    <div class="alert alert-warning oe_edit_only"
                         role="alert">

                        A duplicate value was found for field
                        <strong>{config.field_id.field_description}</strong>

                        <br/><br/>

                        Duplicate Record:
                        <a href="{record_url}" target="_blank">
                            <strong>{duplicate.display_name}</strong>
                        </a>

                        <br/>

                        Company:
                        <strong>{company_name or 'No Company'}</strong>

                        <br/>

                        Current Value:
                        <strong>{display_value}</strong>

                    </div>
                """)

            record.dynamic_duplicate_warning = ''.join(warnings)

    # =====================================================
    # CREATE
    # =====================================================

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        records._validate_dynamic_required()

        records._validate_prevent_duplicates()

        return records

    # =====================================================
    # WRITE
    # =====================================================

    def write(self, vals):

        res = super().write(vals)

        self._validate_dynamic_required(vals)

        self._validate_prevent_duplicates(vals)

        return res


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def postprocess_and_fields(self, node, model=None, **options):
        # First let Odoo perform its normal view processing
        arch, fields = super().postprocess_and_fields(
            node,
            model=model,
            **options
        )

        # No model = nothing to configure
        if not model:
            return arch, fields

        # During module loading the model may not yet be
        # available in the registry.
        if 'required.field.config' not in self.env:
            return arch, fields

        Config = self.env['required.field.config']

        # IMPORTANT:
        # During installation/upgrade the Python model may already
        # exist in the registry while its PostgreSQL table has not
        # been created yet.
        #
        # Do NOT search before this check, otherwise PostgreSQL logs:
        # relation "required_field_config" does not exist
        if not sql.table_exists(self.env.cr, Config._table):
            return arch, fields

        # Get all dynamic configurations for this model in one query
        configs = Config.sudo().search([
            ('model_id.model', '=', model),
        ])

        if not configs:
            return arch, fields

        # Parse the processed XML architecture
        try:
            doc = etree.XML(arch)
        except (etree.XMLSyntaxError, TypeError, ValueError):
            return arch, fields

        # =====================================================
        # DYNAMIC REQUIRED FIELDS
        # =====================================================

        required_configs = configs.filtered(
            lambda config: config.required
        )

        for config in required_configs:
            field_name = config.field_id.name

            if not field_name:
                continue

            field_nodes = doc.xpath(
                "//field[@name='%s']" % field_name
            )

            for field_node in field_nodes:
                field_node.set('required', '1')

        # =====================================================
        # DYNAMIC DUPLICATE WARNING
        # =====================================================

        warning_configs = configs.filtered(
            lambda config: config.duplicate_warning
        )

        if warning_configs:
            # Warning is useful only inside form views
            form_nodes = doc.xpath("//form")

            if form_nodes:
                existing_warning = doc.xpath(
                    "//field[@name='dynamic_duplicate_warning']"
                )

                # Don't insert the field twice
                if not existing_warning:
                    warning_node = etree.Element(
                        'field',
                        name='dynamic_duplicate_warning',
                        widget='html',
                        nolabel='1',
                        readonly='1',
                    )

                    # Put warning at the beginning of the form
                    form_nodes[0].insert(0, warning_node)

        # Convert modified XML back to string
        arch = etree.tostring(
            doc,
            encoding='unicode'
        )

        return arch, fields