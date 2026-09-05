from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class DeMultiAdmissionWizard(models.TransientModel):
    _name = "de.multi.admission.wizard"
    _description = "Multi Admission Wizard"

    # fee fields
    fee_start_date = fields.Date('fee Start Date')

    fee = fields.Float('Register Fee amount', related="grade_id.product_id.lst_price", readonly=True, store=True)
    discount = fields.Float(string='Discount (%)',
                            digits='Discount', default=0.0)

    fee_term_id = fields.Many2one('de.fee.term', 'fee Term', readonly=True, store=True,
                                  related="grade_id.fee_term_id")
    fee_term_type = fields.Char(readonly=True, store=True, compute="compute_fee_term")

    fee_after_discount = fields.Float('Fee after discount', readonly=True, store=True,
                                      compute="compute_fee_after_discount")

    # student fields
    prev_institute_id = fields.Char('Previous Institute',
                                    )
    prev_grade_id = fields.Char('Previous Grade',
                                )
    prev_result = fields.Char(
        'Previous Result', size=256)
    family_business = fields.Char(
        'Family Business', size=256)
    family_income = fields.Integer(
        'Family Income')

    # admission fields
    academic_year_id = fields.Many2one(
        'de.academic.year', string='Academic year', required=True
    )
    grade_id = fields.Many2one('de.grade', 'Grade', required=True)
    student_count = fields.Integer('Enrolled Students number count', related="grade_id.student_count", readonly=True,
                                   store=True)
    max_student_count = fields.Integer('Grade capacity count', compute="_compute_max_student_count", readonly=True,
                                       store=True)
    to_enroll_students_count = fields.Integer('To enroll students count', compute="_compute_to_enroll_students_count",
                                              readonly=True,
                                              store=True)
    student_capacity = fields.Integer('Students capacity', compute="_compute_student_capacity",
                                      readonly=True,
                                      store=True)

    student_ids = fields.Many2many(
        'de.student', string='Student', required=True)

    @api.depends('discount', 'fee')
    def compute_fee_after_discount(self):
        for record in self:
            record.fee_after_discount = record.fee - ((record.fee * record.discount) / 100)

    @api.depends('grade_id')
    def _compute_max_student_count(self):
        for rec in self:
            rec.max_student_count = rec.grade_id.max_student_count

    @api.depends('student_ids')
    def _compute_to_enroll_students_count(self):
        for rec in self:
            rec.to_enroll_students_count = len(rec.student_ids)

    @api.depends('student_ids', 'grade_id')
    def _compute_student_capacity(self):
        for rec in self:
            rec.student_capacity = rec.max_student_count - (rec.student_count + len(rec.student_ids))

    def do_action(self):
        students = self.student_ids
        data_list = []
        for rec in students:
            object = {}
            object['student_id'] = rec.id
            object['academic_year_id'] = self.academic_year_id.id
            object['grade_id'] = self.grade_id.id
            object['discount'] = self.discount
            object['fee_start_date'] = self.fee_start_date
            object['prev_institute_id'] = self.prev_institute_id

            object['prev_grade_id'] = self.prev_grade_id

            object['prev_result'] = self.prev_result

            object['family_business'] = self.family_business

            object['family_income'] = self.family_income
            data_list.append(object)
            object = {}

        if self.student_count + len(self.student_ids) > self.max_student_count:
            raise ValidationError(_(
                f'({self.grade_id.name}) Student capacity limit ({self.max_student_count}) has been exceeded'))

        admissions = self.env['de.admission'].create(data_list)
        admissions.set_confirm()

        action = self.env.ref('dekad_admission.act_open_de_admission_view').read()[0]
        action['target'] = 'main'
        return action
