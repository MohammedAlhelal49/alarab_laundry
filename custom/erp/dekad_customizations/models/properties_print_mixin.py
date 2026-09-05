from odoo import _, fields, models


class PropertiesPrintMixin(models.AbstractModel):
    _name = "properties.print.mixin"
    _description = "Properties Print Mixin"

    def get_property_print_value(self, prop):
        """Return the printable value of a property definition."""
        self.ensure_one()

        prop_type = prop.get("type")
        prop_name = prop.get("name")

        values = self.custom_properties or {}
        value = values.get(prop_name, prop.get("default"))

        # Separator
        if prop_type == "separator":
            return ""

        # Boolean
        if prop_type == "boolean":
            return _("Yes") if value else _("No")

        # Empty value
        if value in (False, None, ""):
            return ""

        # Text / Integer / Decimal
        if prop_type in ("char", "integer", "float"):
            return str(value)

        # Date
        if prop_type == "date":
            try:
                date_value = fields.Date.to_date(value)
                return fields.Date.to_string(date_value)
            except (TypeError, ValueError):
                return str(value)

        # Date & Time
        if prop_type == "datetime":
            try:
                datetime_value = fields.Datetime.to_datetime(value)
                return fields.Datetime.to_string(datetime_value)
            except (TypeError, ValueError):
                return str(value)

        # Selection
        if prop_type == "selection":
            options = dict(prop.get("selection") or [])
            return str(options.get(value, value))

        # Tags
        if prop_type == "tags":
            tags = prop.get("tags") or []

            tags_dict = {
                tag[0]: tag[1]
                for tag in tags
                if len(tag) >= 2
            }

            if isinstance(value, (list, tuple)):
                return ", ".join(
                    str(tags_dict.get(item, item))
                    for item in value
                )

            return str(tags_dict.get(value, value))

        # Many2one
        if prop_type == "many2one":
            comodel = prop.get("comodel")

            if not comodel:
                return str(value)

            if isinstance(value, int):
                record = self.env[comodel].browse(value).exists()
                return record.display_name if record else ""

            if isinstance(value, (list, tuple)) and len(value) >= 2:
                return str(value[1])

            return str(value)

        # Many2many
        if prop_type == "many2many":
            comodel = prop.get("comodel")

            if not value:
                return ""

            if isinstance(value, (list, tuple)):

                # [[id, display_name], ...]
                if value and isinstance(value[0], (list, tuple)):
                    return ", ".join(
                        str(item[1])
                        for item in value
                        if len(item) >= 2
                    )

                # [1, 2, 3]
                if comodel and all(isinstance(item, int) for item in value):
                    records = self.env[comodel].browse(value).exists()
                    return ", ".join(records.mapped("display_name"))

            return str(value)

        return str(value)