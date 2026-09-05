from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeClassroom(models.Model):
    _name = "de.classroom"
    _description = "Classroom"

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', help="Used for sorting classrooms", copy=False)
    grade_id = fields.Many2one('de.grade', 'Grade', required=True)
    capacity = fields.Integer(string='Student capacity', default=30, required=True)
    asset_ids = fields.One2many('de.asset', 'classroom_id', string='Assets')
    student_ids = fields.One2many('de.student', 'classroom_id', string='Students', copy=False)
    all_selected_student_ids = fields.Many2many(
        'de.student', 'classroom_all_selected_student_rel',
        'classroom_id', 'student_id', string="All Selected students", compute="_compute_all_selected_student_ids")

    filtered_students = fields.Many2many('de.student', 'classroom_filtered_student_rel',
                                         'classroom_d', 'student_id', string="Classroom filtered students",
                                         compute="_compute_filtered_students")
    all_classroom_student = fields.Char('Selected students ids stored as string')

    student_count = fields.Integer(store=True, readonly=True, compute="_compute_student_count", string="Student")
    filtered_student_count = fields.Integer(store=True, readonly=True, compute="_compute_filtered_student_count",
                                            string="Filtered student")
    active = fields.Boolean(default=True)

    @api.constrains('asset_ids', 'asset_ids.qty')
    def check_asset_count(self):
        for rec in self:
            for asset in rec.asset_ids:
                if asset.qty <= 0:
                    raise ValidationError('Please enter proper assets quantity value')

    @api.onchange('grade_id')
    def onchange_grade(self):
        for rec in self:
            rec.student_ids = False

    @api.constrains('capacity', 'student_count')
    def _check_count_capacity(self):
        for rec in self:
            if rec.student_count > rec.capacity:
                raise ValidationError('Students count is more than the classroom student capacity ')

    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity <= 0:
                raise ValidationError("Please enter proper capacity!")

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.depends('filtered_students')
    def _compute_filtered_student_count(self):
        for rec in self:
            rec.filtered_student_count = len(rec.filtered_students)

    @api.depends('grade_id', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.grade_id.name} - {rec.name}"

    def action_show_student(self):
        action = self.env.ref('dekad_core.act_open_de_student_view').read()[0]
        action['domain'] = [('classroom_id', '=', self.id)]
        action['context'] = {'create': False, 'edit': False}
        return action

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + "(copy)"
        return super(DeClassroom, self).copy(default)

    @api.model_create_multi
    def create(self, vals):
        res = super(DeClassroom, self).create(vals)
        self._assign_Destem_parameter_students()
        return res

    def write(self, vals):
        res = super(DeClassroom, self).write(vals)
        self._assign_Destem_parameter_students()
        return res

    def unlink(self):
        res = super(DeClassroom, self).unlink()
        self._assign_Destem_parameter_students()
        return res

    def clear_all_students(self):
        self.student_ids = False

    @api.depends('student_ids')
    def _compute_all_selected_student_ids(self):
        students_ids_list = [int(x) for x in self.get_param().split(",")] if self.get_param() != False else []
        for rec in self:
            selected_ids = []
            if len(rec.student_ids):
                for record in rec.student_ids:
                    selected_ids.append(record.id if isinstance(record.id, int) else int(str(record.id).split("_")[1]))
            rec.write({'all_selected_student_ids': [
                (6, 0, list(filter(lambda x: x not in selected_ids, students_ids_list)))]})
    #
    def _assign_Destem_parameter_students(self):
        students_ids = []
        for classroom in self.env['de.classroom'].search([]):
            
            for item in classroom.student_ids.ids:
                students_ids.append(item)
        allocated_students_ids = self.env['de.student'].browse(students_ids).ids
        parameter_name = 'dekad_classroom.allocated_students'
        config_parameter = self.env['ir.config_parameter'].sudo()
        result_string = ','.join(map(str, allocated_students_ids))
        config_parameter.set_param(parameter_name, result_string if len(allocated_students_ids) else "")

    def get_param(self):
        parameter_name = 'dekad_classroom.allocated_students'
        config_parameter = self.env['ir.config_parameter'].sudo()
        return config_parameter.get_param(parameter_name)

    # classrooms students filter
    @api.constrains('grade_id', 'name')
    def check_name(self):
        if self.search_count(
                [('name', '=', self.name), ('grade_id', '=', self.grade_id.id)]) > 1:
            raise ValidationError(_(
                f"Classroom Name must be unique inside the grade"))

    @api.depends('grade_id', 'grade_id.student_grade_ids', 'all_selected_student_ids')
    def _compute_filtered_students(self):
        for rec in self:
            filter_list = [('id', 'not in', self.all_selected_student_ids.ids),
                           ('student_grade_ids.grade_id', '=', self.grade_id.id),
                           ('student_grade_ids.state', '=', 'running')]
            rec.filtered_students = self.env['de.student'].search(filter_list)
    def name_get(self):
        vals = []
        for record in self:
            vals.append((record.id, f"{record.grade_id.name} - {record.name}"))
        return vals