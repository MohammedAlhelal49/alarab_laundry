# -*- coding: utf-8 -*-
###############################################################################
#
#    DencCode Inc
#    Copyright (C) 2009-TODAY DencCode Inc(<http://www.dekad.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _


class DeLeave(models.Model):
    _name = "de.leave"
    _inherit = "mail.thread"
    _description = "Students leaves manage"
    _order = "create_date DESC"
    _rec_name = "sequence"

    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].sudo().next_by_code('de.leave'))

    leave_type = fields.Many2one('de.leave.type',
                                 string='Type', required=True)

    student_id = fields.Many2one(
        'de.student', 'Student', default=lambda self: self.env[
            'de.student'].search([('user_id', '=', self.env.uid)]),
        required=True, ondelete="cascade")

    parent_id = fields.Many2one(
        'de.parent', 'Parent', default=lambda self: self.env[
            'de.parent'].search([('user_id', '=', self.env.uid)]),
    )

    description = fields.Text('Description')

    start_date = fields.Date('Start Date', required=True)

    end_date = fields.Date('End Date', required=True)


    duration = fields.Char('Duration', readonly=True, store=True, compute="_compute_duration")

    active = fields.Boolean(default=True)

    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name", copy=False)  # Added by Ahmed
    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'confirmed'), ('reject', 'Rejected'), ('accept', 'Accepted')
        , ('start', 'Started'), ('finish', 'Finished')
    ], 'State', required=True, default='draft', tracking=True, copy=False)

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date == record.end_date:
                    record.duration = f'{1} Day'
                else:
                    duration = (record.end_date - record.start_date).days
                    record.duration = f'{duration + 1} Days'

            else:
                record.duration = ''

    @api.constrains('start_date', 'end_date', 'student_id')
    def _check_date(self):
        ssd = self.start_date
        sed = self.end_date
        ssi = self.student_id
        if ssd > sed:
            raise models.ValidationError(_(
                'End Date cant be less than Start Date.'))
        if ssd < fields.date.today():
            raise models.ValidationError(_(
                'Start Date cant be less than today'))
        leaves = self.env['de.leave'].search([])
        for leave in leaves:
            rsd = leave.start_date
            red = leave.end_date
            if self.id != leave.id:
                if ssi == leave.student_id and ssd == rsd and sed == red:
                    raise models.ValidationError(_(
                        f'Student already have this leave ({rsd} - {red})'))
                self_leave_inside_request_leave = (rsd < ssd < red) or (rsd < sed < red)
                request_leave_inside_self_leave = (ssd < rsd < sed) or (ssd < red < sed)
                if ssi == leave.student_id and (
                        self_leave_inside_request_leave or request_leave_inside_self_leave):
                    raise models.ValidationError(_(
                        f'Student leave overlap in another leave ({rsd} - {red})'))


    def set_confirm(self):
        self.state = 'confirm'

    def set_accept(self):
        self.state = 'accept'

    def set_cancel(self):
        self.state = 'confirm'

    def set_reject(self):
        self.state = 'reject'

    def set_draft(self):
        self.state = 'draft'

    def set_start(self):
        self.state = 'start'

    def set_finish(self):
        self.state = 'finish'

    def cron_start_finish_leave_state(self):
        for record in self.search([]):
            if record.start_date == fields.date.today() and record.state == 'accept':
                record.set_start()
            if record.end_date == fields.date.today() and record.state == 'start':
                record.set_finish()

    def name_get(self):
        result = []
        for record in self:
            if record.sequence:
                name = record.sequence
            elif record.student_id and record.leave_type:
                name = f"{record.student_id.name} - {record.leave_type.name}"
            elif record.student_id:
                name = f"{record.student_id.name} - Leave"
            elif record.description:
                name = record.description[:50] + ('...' if len(record.description) > 50 else '')
            else:
                name = f'Leave #{record.id}' if record.id else 'New Leave'
            result.append((record.id, name))
        return result