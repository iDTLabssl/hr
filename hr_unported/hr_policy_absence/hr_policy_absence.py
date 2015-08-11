# -*- coding:utf-8 -*-
#
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from openerp.osv import fields, orm
from openerp import models, fields, api


class policy_absence(orm.Model):

    _name = 'hr.policy.absence'

    name = fields.Char('Name', size=128, required=True)
    date = fields.Date('Effective Date', required=True)
    line_ids = fields.One2many(
            'hr.policy.line.absence', 'policy_id', 'Policy Lines')

    # Return records with latest date first
    _order = 'date desc'

    @api.model
    def get_codes(self):

        res = []
        [res.append(
            (line.code, line.name, line.type, line.rate, line.use_awol))
         for line in self.browse().line_ids]
        return res

    @api.model
    def paid_codes(self):

        res = []
        [res.append((line.code, line.name))
         for line in self.browse().line_ids if line.type == 'paid']
        return res
   
    @api.model
    def unpaid_codes(self):

        res = []
        [res.append((line.code, line.name))
         for line in self.browse().line_ids if line.type == 'unpaid']
        return res


class policy_line_absence(orm.Model):

    _name = 'hr.policy.line.absence'

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char(
            'Code', required=True, help="Use this code in the salary rules.")
    holiday_status_id = fields.Many2one(
            'hr.holidays.status', 'Leave', required=True)
    policy_id = fields.Many2one('hr.policy.absence', 'Policy')
    type = fields.Selection(
            [
                ('paid', 'Paid'),
                ('unpaid', 'Unpaid'),
                ('dock', 'Dock')
            ],
            'Type',
            required=True,
            help="Determines how the absence will be treated in payroll. "
                 "The 'Dock Salary' type will deduct money (useful for "
                 "salaried employees).",
        )
    
    rate = fields.Float(
            'Rate', required=True, help='Multiplier of employee wage.')
    use_awol = fields.Boolean(
            'Absent Without Leave',
            help='Use this policy to record employee time absence not covered '
                 'by other leaves.'
        )

    @api.onchange('holiday_status_id')
    def onchange_holiday(self, holiday_status_id):

        res = {'value': {'name': False, 'code': False}}
        if not holiday_status_id:
            return res
        data = self.pool.get(
            'hr.holidays.status').read(
                holiday_status_id, ['name', 'code'])
        res['value']['name'] = data['name']
        res['value']['code'] = data['code']
        return res


class policy_group(orm.Model):

    _name = 'hr.policy.group'
    _inherit = 'hr.policy.group'

    absence_policy_ids = fields.Many2many(
            'hr.policy.absence', 'hr_policy_group_absence_rel',
            'group_id', 'absence_id', 'Absence Policy')
