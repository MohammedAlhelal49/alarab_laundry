from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeSpecialist(models.Model):
    _name = 'de.specialist'
    _description = ' Teacher Specialist'
    name = fields.Char(string='Specialist Name', required=True)
    _sql_constraints = [('unique_name', 'unique(name)', 'Name must be unique per  teacher specialist!')]


class DeTeacher(models.Model):
    _name = 'de.teacher'
    _description = ' Teacher'
    _inherit = ['mail.thread']
    _inherits = {'res.partner': 'partner_id'}
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')

    # name fields
    first_name = fields.Char(string='First Name')
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    detailed_name = fields.Boolean(string='Detailed Name')

    # emirate id fields
    emirate_id = fields.Char(string='Emirate Id')
    emirate_id_expiry_date = fields.Date(string='Emirate Id Expiry Date')

    # personal fields and sequence
    birth_date = fields.Date(string='Birth Date')
    address = fields.Char(string='Full Address')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', required=True)
    visa_info = fields.Char(string='Visa Info', size=64)
    sequence = fields.Char('Sequence', readonly=True, store=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.teacher'))

    # user access fields
    user_id = fields.Many2one('res.users', 'User')
    login = fields.Char('Login', related='partner_id.user_id.login', readonly=True)
    last_login = fields.Datetime('Latest Connection', readonly=True,
                                 related='partner_id.user_id.login_date')
    active = fields.Boolean(default=True)

    # HR Employee link with cascade delete
    employee_id = fields.Many2one('hr.employee', string='Related Employee',
                                  readonly=True, copy=False,
                                  ondelete='cascade',
                                  help="Link to HR Employee record")

    # subjects and grades and students and specialist fields
    subject_ids = fields.Many2many('de.subject', string='Subject(s)', tracking=True)
    grade_ids = fields.Many2many('de.grade', string="Grades", store=True, readonly=True,
                                 compute="_compute_grade_ids")
    student_ids = fields.Many2many('de.student', string="Students", store=True, readonly=True,
                                   compute="_compute_student_ids")
    specialist_id = fields.Many2one('de.specialist', string="Specialist")

    @api.onchange('grade_ids.student_grade_ids', 'student_ids', 'grade_ids')
    def onchange_student_ids(self):
        for rec in self:
            rec.user_id.student_ids = rec.student_ids

    @api.depends('grade_ids', 'grade_ids.student_grade_ids')
    def _compute_student_ids(self):
        for record in self:
            record.student_ids = record.grade_ids.mapped('student_grade_ids').filtered(
                lambda r: r.state == 'running').mapped('student_id')

    @api.depends('subject_ids')
    def _compute_grade_ids(self):
        for record in self:
            record.grade_ids = self.env['de.grade'].search([('subject_ids', 'in', record.subject_ids.ids)])

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        if self.first_name and self.middle_name and self.last_name:
            self.name = str(self.first_name) + " " + str(self.middle_name) + " " + str(self.last_name)

    def create_employee(self):
        """Create HR Employee record linked to this teacher"""
        self.ensure_one()

        if self.employee_id:
            raise ValidationError(_('This teacher already has an associated employee record.'))

        # Prepare employee values
        employee_vals = {
            'name': self.name,
            'work_email': self.email,
            'work_phone': self.phone or self.mobile,
            'mobile_phone': self.mobile,
            'birthday': self.birth_date,
            'gender': self.gender,
            'country_id': self.country_id.id if self.country_id else False,
            'address_id': self.partner_id.id,
            'user_id': self.user_id.id if self.user_id else False,
            'notes': f'Created from Teacher: {self.sequence}',
            'teacher_id': self.id,  # Set reverse relationship
        }

        # Create the employee
        employee = self.env['hr.employee'].create(employee_vals)

        # Link the employee to the teacher
        self.employee_id = employee.id

        # Log the creation in chatter
        self.message_post(
            body=_('HR Employee record created: %s', employee.name),
            subject=_('Employee Created')
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_employee(self):
        """Open the related employee record"""
        self.ensure_one()

        if not self.employee_id:
            raise ValidationError(_('No employee record is linked to this teacher.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def create_user(self):
        user_group = self.env.ref('dekad_core.group_de_teacher') or False
        users_res = self.env['res.users']
        for rec in self:
            if not rec.user_id:
                user_id = users_res.create({
                    'name': rec.name,
                    'partner_id': rec.partner_id.id,
                    'login': rec.email,
                    'is_teacher': rec.is_teacher,
                    'student_ids': rec.student_ids.ids,
                })
                rec.user_id = user_id
                if user_group:
                    user_group.users = user_group.users + user_id

    def cron_clear_unused_contact(self):
        teacher_env = self.env['de.teacher']
        teacher_contacts = teacher_env.search([]).mapped('partner_id')
        contacts = self.env['res.partner'].search([('is_teacher', '=', True)])
        for item in contacts:
            if item not in teacher_contacts:
                item.unlink()

    def unlink(self):
        """Override unlink to cascade delete employee records"""
        employees_to_delete = self.env['hr.employee']

        for rec in self:
            # Collect employee records to delete
            if rec.employee_id:
                employees_to_delete |= rec.employee_id

            # Delete user if exists
            if rec.user_id:
                rec.user_id.unlink()

        # Call super to delete teacher records
        res = super(DeTeacher, self).unlink()

        # Delete collected employee records after teacher deletion
        if employees_to_delete:
            employees_to_delete.unlink()

        return res

    @api.model_create_multi
    def create(self, vals):
        self.env['res.users'].check_role_email_duplication({'id': 0, 'role': 'teacher', 'email': vals[0]['email']})
        self.env['res.users'].check_role_name_duplication({'id': 0, 'role': 'teacher', 'name': vals[0]['name']})
        res = super(DeTeacher, self).create(vals)
        res.is_teacher = True
        return res

    @api.constrains('email')
    def check_role_email(self):
        self.env['res.users'].check_role_email_duplication({'id': self.id, 'role': 'teacher', 'email': self.email})

    @api.constrains('name')
    def check_role_name(self):
        self.env['res.users'].check_role_name_duplication({'id': self.id, 'role': 'teacher', 'name': self.name})


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    teacher_id = fields.Many2one('de.teacher', string='Related Teacher',
                                 readonly=True, copy=False,
                                 ondelete='cascade',
                                 help="Link to Teacher record")

    def action_open_teacher(self):
        """Open the related teacher record"""
        self.ensure_one()

        if not self.teacher_id:
            raise ValidationError(_('No teacher record is linked to this employee.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Teacher'),
            'res_model': 'de.teacher',
            'res_id': self.teacher_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        """Override unlink to cascade delete teacher records"""
        teachers_to_delete = self.env['de.teacher']

        for rec in self:
            # Find teacher records linked to this employee
            teacher = self.env['de.teacher'].search([('employee_id', '=', rec.id)], limit=1)
            if teacher:
                teachers_to_delete |= teacher

        # Call super to delete employee records
        res = super(HrEmployee, self).unlink()

        # Delete collected teacher records after employee deletion
        if teachers_to_delete:
            # Use sudo to bypass access rights if needed
            teachers_to_delete.sudo().unlink()

        return res