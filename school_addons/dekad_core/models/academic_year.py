from odoo import models, fields, api, exceptions, _
from datetime import timedelta


class DeAcademicYear(models.Model):
    _name = 'de.academic.year'
    _description = "Academic Year"

    name = fields.Char('Name', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

    academic_term_ids = fields.One2many('de.academic.term', 'academic_year_id',
                                        string='Academic Terms')

    _sql_constraints = [
        ('unique_name',
         'unique(name)', 'Name should be unique per Academic year!')
    ]

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        academic_years = self.search([])
        ssd = self.start_date
        sed = self.end_date
        if ssd >= sed:
            raise models.ValidationError(_(
                'End Date cant be less than The Start Date.'))
        for year in academic_years:
            rsd = year.start_date
            red = year.end_date
            if self.id != year.id:
                if ssd == rsd and sed == red:
                    raise models.ValidationError(_(
                        f'Academic year already exist ({rsd} - {red})'))
                self_year_inside_request_year = (rsd < ssd < red) or (rsd < sed < red)
                request_year_inside_self_year = (ssd < rsd < sed) or (ssd < red < sed)
                if self_year_inside_request_year or request_year_inside_self_year:
                    raise models.ValidationError(_(
                        f'Academic Year overlap in another one ({rsd} - {red})'))

    # @api.constrains('academic_term_ids')
    # def _check_term(self):
    #     for rec in self:
    #         if rec.academic_term_ids and len(rec.academic_term_ids) != 3:
    #             raise exceptions.ValidationError(_("Academic year must have 3 terms!"))
