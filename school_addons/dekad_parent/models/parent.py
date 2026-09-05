from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class DeParent(models.Model):
    _name = "de.parent"
    _description = "Parent"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}

    partner_id = fields.Many2one('res.partner', 'Contacts', required=True, ondelete="cascade")

    # name fields
    first_name = fields.Char(string="First Name")
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    detailed_name = fields.Boolean(string='Detailed Name')

    # emirate id fields
    emirate_id = fields.Char(string='Emirate Id')
    emirate_id_expiry_date = fields.Date(string='Emirate Id Expiry Date')

    # personal fields and sequence
    birth_date = fields.Date(string='Birth Date')
    address = fields.Char(string='Full Address')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string=
    'Gender', required=True)
    visa_info = fields.Char(string='Visa Info', size=64)
    sequence = fields.Char(string='Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.parent'))

    # user access fields
    user_id = fields.Many2one('res.users', string="User")
    login = fields.Char('Login', related='partner_id.user_id.login', readonly=True)
    last_login = fields.Datetime('Latest Connection', readonly=True, related='partner_id.user_id.login_date')
    active = fields.Boolean(default=True)

    # relation and student fields
    relationship_id = fields.Many2one('de.parent.relationship', string='Relationship with student', required=True)
    student_ids = fields.Many2many('de.student', string='Students', copy=False)
    student_count = fields.Integer(compute='_compute_student_count', readonly=True, store=True)

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        if self.first_name and self.middle_name and self.last_name:
            self.name = str(self.first_name) + " " + str(self.middle_name) + " " + str(self.last_name)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('email') and not default.get('name'):
            default['email'] = self.email + "(copy)"
            default['name'] = self.name + "(copy)"
        return super(DeParent, self).copy(default)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_show_student(self):
        action = self.env.ref('dekad_core.act_open_de_student_view').read()[0]
        action['domain'] = [('id', 'in', self.student_ids.ids)]
        return action

    @api.model_create_multi
    def create(self, vals):
        self.env['res.users'].check_role_email_duplication({'id': 0, 'role': 'parent', 'email': vals[0]['email']})
        self.env['res.users'].check_role_name_duplication({'id': 0, 'role': 'parent', 'name': vals[0]['name']})

        # import parents from excel => handle the gender
        # for val in vals:
        #     # if not val['gender']:
        #     relation = self.env['de.parent.relationship'].browse(val['relationship_id'])
        #     if relation.name == 'Father':
        #         val['gender'] = 'male'
        #     if relation.name == 'Mother':
        #         val['gender'] = 'female'
        #     if relation.name == 'Self':
        #         val['gender'] = 'male'
        #     if relation.name == 'Step-Mother':
        #         val['gender'] = 'female'
        #     if relation.name == 'Aunt':
        #         val['gender'] = 'female'
        #     if relation.name == 'Brother':
        #         val['gender'] = 'male'
        #     if relation.name == 'Sister':
        #         val['gender'] = 'female'
        res = super(DeParent, self).create(vals)
        res.is_parent = True
        return res

    @api.constrains('email')
    def check_role_email(self):
        self.env['res.users'].check_role_email_duplication({'id': self.id, 'role': 'parent', 'email': self.email})

    @api.constrains('name')
    def check_role_name(self):
        self.env['res.users'].check_role_name_duplication({'id': self.id, 'role': 'parent', 'email': self.name})

    def unlink(self):
        for rec in self:
            rec.user_id.unlink() if rec.user_id else 1 == 1
        return super(DeParent, self).unlink()

    def create_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        print(users_res)
        for record in self:
            if not record.user_id:
                user_ids = record.student_ids.mapped('user_id').ids
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.email,
                    'groups_id': user_group,
                    'is_parent': record.is_parent,
                    'tz': self._context.get('tz'),
                    'child_ids': [(6, 0, user_ids)],
                })
                record.user_id = user_id

    def write(self, vals):
        for rec in self:
            res = super(DeParent, self).write(vals)
            if vals.get('student_ids', False) and rec.user_id:
                rec.user_id.child_ids = [(6, 0, rec.student_ids.mapped('user_id').ids)]
            rec.clear_caches()
            return res

    def cron_clear_unused_contact(self):
        parent_env = self.env['de.parent']
        parent_contacts = parent_env.search([]).mapped('partner_id')
        contacts = self.env['res.partner'].search([('is_parent', '=', True)])
        for item in contacts:
            if item not in parent_contacts:
                item.unlink()

    def handle_duplication(self):
        duplicated_parents = self.search([])
        unique_parents = []
        for rec in duplicated_parents:
            if not any(obj["name"] == rec.name for obj in unique_parents):
                unique_parents.append(rec)
            else:
                index = next((i for i, obj in enumerate(unique_parents) if obj["name"] == rec.name), None)
                unique_parents[index].student_ids += rec.student_ids
        unique_parents_handled = []
        for rec in unique_parents:
            dict = {}
            dict['name'] = rec.name
            dict['sequence'] = rec.sequence
            dict['visa_info'] = rec.visa_info
            dict['relationship_id'] = rec.relationship_id.id
            dict['student_ids'] = rec.student_ids.ids
            dict['gender'] = rec.gender
            dict['religion_id'] = rec.religion_id.id
            dict['emirate_id'] = rec.emirate_id
            dict['emirate_id_expiry_date'] = rec.emirate_id_expiry_date
            dict['country_id'] = rec.country_id.id
            dict['nationality_id'] = rec.nationality_id.id
            dict['country_group_id'] = rec.country_group_id.id
            dict['address'] = rec.address
            dict['email'] = rec.email
            dict['mobile'] = rec.mobile
            dict['phone'] = rec.phone
            dict['user_id'] = rec.user_id.id
            dict['birth_date'] = rec.birth_date if rec.birth_date else None
            dict['city'] = rec.city
            unique_parents_handled.append(dict)
            dict = {}

        self.env['de.parent'].search([]).unlink()
        self.env['de.parent'].create(unique_parents_handled)
