from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeHoliday(models.Model):
    _name = "de.holiday"
    _description = "School Holidays"

    name = fields.Char(string="Name", required=True)
    date = fields.Date(string="Date")
    start_date = fields.Date(string="Holiday Start Date")
    end_date = fields.Date(string="Holiday End Date")
    is_range = fields.Boolean(string="Range of days")

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Holiday name must be unique!'),
    ]

    @api.onchange('is_range')
    def on_change_is_range(self):
        if self.is_range:
            self.date = False
        else:
            self.start_date = False
            self.end_date = False

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_("Name must be unique per holiday"))

    @api.constrains('date')
    def check_date(self):
        if self.date:
            holidays = self.search([('date', '=', self.date)])
            if len(holidays) > 1:
                raise ValidationError(
                    _(f"THe date ({self.date}) is already used in another holiday ({holidays[0].name})"))
        # Check if a specific date overlaps with a range of dates
        for date_range in self.search([]):
            if date_range.name != self.name and date_range.start_date and date_range.end_date:
                if date_range.start_date <= self.date <= date_range.end_date:
                    raise ValidationError(_(
                        f"Holiday date ({self.date}) overlaps with another holiday range of dates ({date_range.start_date} - {date_range.end_date})"
                    ))

    @api.constrains('start_date', 'end_date')
    def check_date_range(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError(_('The end date must be after the start date'))
            # Check if the date range overlaps with any existing date ranges
            for holiday in self.search([]):
                if holiday.id != self.id:
                    if holiday.is_range:
                        if self.start_date <= holiday.end_date and self.end_date >= holiday.start_date:
                            raise ValidationError(
                                _(f"Holiday ({self.name}) range of dates ({self.start_date} - {self.end_date}) overlaps with another holiday range of dates ({holiday.name}  {holiday.start_date} - {holiday.end_date})"))

                    else:
                        if self.start_date <= holiday.date <= self.end_date:
                            raise ValidationError(_(
                                f"Holiday date ({holiday.date}) overlaps with the range of dates ({self.start_date} - {self.end_date})"))
