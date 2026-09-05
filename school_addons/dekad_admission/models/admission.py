from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeAdmission(models.Model):
    _name = "de.admission"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "sequence"
    _description = "Admission"
    _order = 'admission_date DESC'

    max_student_count = fields.Integer('Grade capacity count', related="grade_id.max_student_count", readonly=True,
                                       store=True)

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

    due_date = fields.Date('Due Date')

    # student fields
    student_id = fields.Many2one('de.student', string='Student', required=True, ondelete="cascade")
    student_id_sequence = fields.Char(string='Student sequence', readonly=True, store=True,
                                      related="student_id.sequence")

    image = fields.Image('image', readonly=True, store=True, related="student_id.image_1920")
    name = fields.Char('Name', size=128, readonly=True, store=True, related="student_id.name")
    birth_date = fields.Date('Birth Date', readonly=True, store=True, related="student_id.birth_date")
    prev_institute_id = fields.Char(' Previous institute')
    prev_grade_id = fields.Char('Previous Grade')
    prev_result = fields.Char('Previous Result', size=256)
    family_business = fields.Char('Family Business', size=256)
    family_income = fields.Integer('Family Income')
    # admission fields

    sequence = fields.Char('Application Number', size=16, readonly=True, store=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.admission'), copy=False)
    admission_date = fields.Date('Admission Date', readonly=True, store=True, copy=False)
    academic_year_id = fields.Many2one('de.academic.year', string='Academic Year', required=True)
    grade_id = fields.Many2one('de.grade', string="Grade")
    student_count = fields.Integer('Enrolled students count', related="grade_id.student_count", readonly=True,
                                   store=True)
    nbr = fields.Integer('No of Admission', readonly=True, copy=False)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], strin='State', default='draft',
                             tracking=True, copy=False)
    active = fields.Boolean(default=True)

    @api.depends('discount', 'fee')
    def compute_fee_after_discount(self):
        for record in self:
            record.fee_after_discount = record.fee - ((record.fee * record.discount) / 100)

    def set_confirm(self):
        for rec in self:
            rec.enroll_student()
            rec.state = 'confirm'

    def set_draft(self):
        self.state = 'draft'

    def set_cancel(self):
        self.student_id.student_grade_ids.unlink()
        self.student_id.student_fee_ids.unlink()
        self.student_id.classroom_id = False
        self.state = 'draft'

    def action_show_student(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Students',
            'view_mode': 'form',
            'res_model': 'de.student',
            'res_id': self.student_id.id,
            'target': ':current',
        }

    def enroll_student(self):
        for record in self:
            student_id = record.student_id.id
            student_grade = self.env['de.student.grade'].create(
                {
                    'grade_id':
                        record.grade_id and record.grade_id.id or False,
                    'student_id':
                        record.student_id and record.student_id.id or False,
                    'academic_year_id': record.academic_year_id.id or False,
                    'subject_ids': [(6, 0, record.grade_id.subject_ids.ids)],
                    'fee_term_id': record.fee_term_id.id,
                    'fee_start_date': record.fee_start_date,
                    'product_id': record.grade_id.product_id.id,
                }
            )

            record.write({
                'nbr': 1,
                'admission_date': fields.Date.today()
            })

            # add the student fee details records
            val = []
            product_id = record.grade_id.product_id.id

            for line in record.fee_term_id.fee_term_line_ids:
                no_days = line.due_days
                per_amount = line.value
                amount = (per_amount * record.fee) / 100
                dict_val = {
                    'fee_term_line_id': line.id,
                    'amount': amount,
                    'fees_factor': per_amount,
                    'discount': record.discount,
                    'product_id': product_id,
                    'grade_id': record.grade_id and record.grade_id.id or False,
                }
                if line.due_date:
                    date = line.due_date
                    dict_val.update({
                        'date': date
                    })
                elif self.fee_start_date:
                    date = self.fee_start_date + relativedelta(
                        days=no_days)
                    dict_val.update({
                        'date': date,
                    })
                else:
                    date_now = (datetime.today() + relativedelta(
                        days=no_days)).date()
                    dict_val.update({
                        'date': date_now,
                    })
                val.append([0, False, dict_val])
            record.student_id.write({
                'student_fee_ids': val
            })

    def unlink(self):
        for rec in self:
            student = rec.student_id
            if student:
                student.classroom_id = False
                student.student_grade_ids.unlink() if student.student_grade_ids else 1 == 1
                student.student_fee_ids.unlink() if student.student_fee_ids else 1 == 1
        return super(DeAdmission, self).unlink()

    @api.constrains('student_id', "grade_id")
    def _check_grade_admission(self):
        for rec in self:
            if not rec.student_count < rec.max_student_count:
                if rec.max_student_count == 0:
                    msg = f'({rec.grade_id.name}) dosent have student capacity , (you have to add classrooms inside this grade)'
                else:
                    msg = f'({rec.grade_id.name}) Student capacity limit ({rec.max_student_count}) has been exceeded'
                raise ValidationError(_(msg))

            # student count limit
            running_grade = rec.student_id.student_grade_ids.filtered(
                lambda r: r.state == 'running')

            if running_grade:
                raise ValidationError(_(
                    f"Student {rec.student_id.name} didnt finish the {running_grade[0].grade_id.name}"))

            grade_exist_and_not_fail = rec.student_id.student_grade_ids.filtered(
                lambda r: r.state != 'fail' and r.grade_id.id == rec.grade_id.id)

            if grade_exist_and_not_fail:
                raise ValidationError(_(
                    f"Student {rec.student_id.name} cant register in already registered Grade ({grade_exist_and_not_fail[0].grade_id.name}) if he didnt fail in this grade"))
