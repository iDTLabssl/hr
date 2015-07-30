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


class policy_presence(orm.Model):

    _name = 'hr.policy.presence'

    name = fields.char('Name', size=128, required=True)
    date = fields.date('Effective Date', required=True)
    work_days_per_month = fields.integer(
            'Working Days/Month', required=True, default = 26)
    line_ids = fields.One2many(
            'hr.policy.line.presence', 'policy_id', 'Policy Lines')

    # Return records with latest date first
    _order = 'date desc'

    def get_codes(self):

        res = []
        [res.append(
            (line.code, line.name, line.type, line.rate, line.duration))
         for line in self.browse().line_ids]
        return res


class policy_line_presence(orm.Model):

    _name = 'hr.policy.line.presence'

    name = fields.Char('Name', size=64, required=True)
    policy_id = fields.Many2one('hr.policy.presence', 'Policy')
    code = fields.Char(
            'Code', required=True, help="Use this code in the salary rules.")
    rate = fields.Float(
            'Rate', required=True, default = 1.0,
            help='Multiplier of employee wage.')
    type = fields.Selection([('normal', 'Normal Working Hours'),
                                  ('holiday', 'Holidays'),
                                  ('restday', 'Rest Days')]
                                 'Type', required=True)
    active_after = fields.Integer(
            'Active After',
            required=True,
            help='Minutes after first punch of the day in which policy will '
                 'take effect.'
        )
    duration = fields.Integer(
            'Duration', required=True, help="In minutes.")


class policy_group(orm.Model):

    _name = 'hr.policy.group'
    _inherit = 'hr.policy.group'

    presence_policy_ids = fields.Many2many(
            'hr.policy.presence', 'hr_policy_group_presence_rel',
            'group_id', 'presence_id', 'Presence Policy')
