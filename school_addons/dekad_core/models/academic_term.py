from odoo import models, fields, api, _, exceptions


class DeAcademicTerm(models.Model):
    _name = 'de.academic.term'
    _description = "Academic Term"

    name = fields.Char('Name', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    academic_year_id = fields.Many2one(
        'de.academic.year', 'Academic Year', required=True, ondelete="cascade")

    @api.depends('academic_year_id', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.academic_year_id.name} - {rec.name}"

    _sql_constraints = [
        ('unique_name',
         'unique(academic_year_id,name)', 'Academic term Name should be unique per Academic year!')
    ]

    @api.constrains('start_date', 'end_date')
    def _check_date(self):
        academic_year = self[0].academic_year_id
        for rec in self:
            if (rec.start_date >= academic_year.start_date and rec.start_date < academic_year.end_date) and (
                    rec.end_date > academic_year.start_date and rec.end_date <= academic_year.end_date):
                print('valid')
            else:
                raise models.ValidationError(_(
                    f'Academic term ({rec.name}) must be inside the academic year ({academic_year.name})'))

            if rec.start_date >= rec.end_date:
                raise models.ValidationError(_(
                    'End Date cant be less than The Start Date.'))

        # prevent the terms overlap

        academic_terms = self.search([])
        for term in academic_terms:
            for another_term in academic_terms:
                if term.id != another_term.id:
                    ssd = term.start_date
                    sed = term.end_date
                    rsd = another_term.start_date
                    red = another_term.end_date
                    if ssd == rsd and sed == red:
                        raise models.ValidationError(_(
                            f'there are two terms with same start and end date ({term.academic_year_id.name} - {term.name}) and ({another_term.academic_year_id.name} - {another_term.name})'))
                    # print(ssd,sed,rsd,red)
                    # self_term_inside_request_term = (ssd > rsd and ssd < red) or (sed > rsd and sed < red)
                    # request_term_inside_self_year = (rsd > ssd and rsd < sed) or (red > ssd and red < sed)
                    # if self_term_inside_request_term or request_term_inside_self_year:
                    #     raise models.ValidationError(_(
                    #         f'Academic terms ({term.academic_year_id.name} - {term.name}) and ({another_term.academic_year_id.name} - {another_term.name})  overlap in another one'))

                    # if (ssd > rsd and sed < red) and (sed > rsd and sed < red) :
                    #     raise models.ValidationError(_(
                    #         f'The term ({term.academic_year_id.name} - {term.name}) is insede the and ({another_term.academic_year_id.name} - {another_term.name})'))

        for record in academic_terms:
            overlapping_terms = self.search([
                ('id', '!=', record.id),
                '|',
                '&', ('start_date', '<=', record.start_date), ('end_date', '>=', record.start_date),
                '&', ('start_date', '<=', record.end_date), ('end_date', '>=', record.end_date),
            ])
            print(overlapping_terms)
            if overlapping_terms:
                raise exceptions.ValidationError(
                    f"Academic term ({overlapping_terms[0].academic_year_id.name}  - {overlapping_terms[0].name}) overlap in another term.")
