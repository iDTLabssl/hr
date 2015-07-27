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

import time

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp import models, fields, api


class hr_accrual(orm.Model):

    _name = 'hr.accrual'
    _description = 'Accrual'

        name = fields.Char(
            'Name',
            size=128,
            required=True,
        )
        holiday_status_id =  fields.Many2one(
            'hr.holidays.status',
            'Leave',
        )
        line_ids = fields.One2many(
            'hr.accrual.line',
            'accrual_id',
            'Accrual Lines',
            readonly=True,
        )

    def get_balance(self, cr, uid, ids, employee_id, date=None, context=None):

        if date is None:
            date = time.strftime(OE_DATEFORMAT)

        res = 0.0
        #cr.execute('''\
        #SELECT SUM(amount)
        #FROM hr_accrual_line
        #WHERE accrual_id in %s AND employee_id=%s AND date <= %s
        #''', (tuple(ids), employee_id, date))
        
        domain = [('employee_id', '=', self.employee_id), ('date', '<=', self.date)]
        accrual = self.search(domain)

        for row in accrual:
            res = row[0]

        return res


class hr_accrual_line(orm.Model):

    _name = 'hr.accrual.line'
    _description = 'Accrual Line'

        date = fields.Date(
            'Date',
            required=True,
            default = time.strftime(OE_DATEFORMAT)
        ),
        accrual_id = fields.Many2one(
            'hr.accrual',
            'Accrual',
            required=True,
        ),
        employee_id = fields.Many2one(
            'hr.employee',
            'Employee',
            required=True,
        ),
        amount = fields.Float(
            'Amount',
            required=True,
        ),


    _rec_name = 'date'
