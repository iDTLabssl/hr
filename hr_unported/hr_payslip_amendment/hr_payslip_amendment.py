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

from openerp.tools.translate import _
from openerp.osv import fields, orm
from openerp import models, fields, api


class hr_payslip_amendment(orm.Model):

    _name = 'hr.payslip.amendment'
    _description = 'Pay Slip Amendment'

    _inherit = ['mail.thread']

    name = fields.Char(
            'Description',
            size=128,
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    input_id = fields.Many2one(
            'hr.rule.input',
            'Salary Rule Input',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    employee_id = fields.Many2one(
            'hr.employee',
            'Employee',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    amount =  fields.Float(
            'Amount',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
            help="The meaning of this field is dependant on the salary rule "
            "that uses it."
        )
    state = fields.Selection(
            [
                ('draft', 'Draft'),
                ('validate', 'Confirmed'),
                ('cancel', 'Cancelled'),
                ('done', 'Done'),
            ],
            'State',
            required=True,
            readonly=True,
            default = 'draft'
        )
    note = fields.Text(
            'Memo'
        )

    @api.onchange('employee_id')
    def onchange_employee(self, employee_id):

        if not employee_id:
            return {}
        ee = self.env.get('hr.employee').browse(employee_id)
        name = _('Pay Slip Amendment: %s (%s)') % (ee.name, ee.employee_no)
        val = {'name': name}
        return {'value': val}

    @api.multi
    def unlink(self):

        for psa in self.browse():
            if psa.state in ['validate', 'done']:
                raise orm.except_orm(
                    _('Invalid Action'),
                    _('A Pay Slip Amendment that has been confirmed cannot be '
                      'deleted!')
                )

        return super(hr_payslip_amendment, self).unlink()
