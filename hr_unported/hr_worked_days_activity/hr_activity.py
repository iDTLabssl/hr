# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Savoir-faire Linux. All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by
#    the Free Software Foundation, either version 3 of the License, or
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
##############################################################################

from openerp.osv import fields, orm
from openerp import models, fields, api


class hr_activity(orm.Model):
    """
    An activity is a job or a leave type
    When a job or a leave type is created, the related activity is created
    automatically
    """
    _name = 'hr.activity'
    _description = 'Employee Activities'


    @api.multi
    def _get_activity_name(self):
        res = {}

        #if isinstance(ids, (int, long)):
        #    ids = [ids]

        for activity in self.browse():
            if activity.type == 'job' and activity.job_id:
                res[activity.id] = activity.job_id.name_get()[0][1]

            elif activity.type == 'leave' and activity.leave_id:
                res[activity.id] = activity.leave_id.name_get()[0][1]

            else:
                res[activity.id] = ''

        return res

    @api.onchange('type')
    def onchange_activity_type(self):
        return {
            'value': {
                'job_id': 0,
                'leave_id': 0
            }
        }

    name = fields.Char(
            string='Activity Name',
            compute = '_get_activity_name'
        )
    type = fields.Selection(
            (
                ('leave', 'Leave'),
                ('job', 'Job'),
            ),
            'Activity Type',
            required=True
        )
    code = fields.Char(
            'Code',
            help="Used for payslip computation"
        )
    job_id = fields.Many2one(
            'hr.job',
            'Job',
            ondelete='cascade'
        )
    leave_id = fields.Many2one(
            'hr.holidays.status',
            'Leave Type',
            ondelete='cascade'
        )

    _order = 'type'
