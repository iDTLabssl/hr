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

from datetime import datetime
from openerp.tools.translate import _
from openerp.osv import fields, orm
from openerp import models, fields, api


class hr_payroll_run(orm.Model):

    _name = 'hr.payslip.run'
    _inherit = 'hr.payslip.run'

    register_id = fields.Many2one('hr.payroll.register', 'Register'),


class hr_payroll_register(orm.Model):

    _name = 'hr.payroll.register'

    name = fields.Char('Description', size=256, default = '_get_default_name')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('close', 'Close'),
        ], 'Status', select=True, readonly=True,
            default = 'draft')
        
    date_start = fields.Datetime(
            'Date From', required=True, readonly=True,
            states={'draft': [('readonly', False)]}
        )
    date_end = fields.Datetime(
            'Date To', required=True, readonly=True,
            states={'draft': [('readonly', False)]}
        )
    run_ids = fields.One2many(
            'hr.payslip.run', 'register_id', readonly=True,
            states={'draft': [('readonly', False)]}
        )
    company_id = fields.Many2one('res.company', 'Company', default = '_get_company')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)',
            _('Payroll Register description must be unique.')),
    ]

    @api.model
    def _get_default_name(self):

        nMonth = datetime.now().strftime('%B')
        year = datetime.now().year
        name = _('Payroll for the Month of %s %s' % (nMonth, year))
        return name

    @api.model
    def _get_company(self):

        users_pool = self.env.get('res.users')
        return users_pool.browse(
                                 users_pool.search(
                                      [(
                                         'id', '=', uid)])).company_id.id


    @api.model
    def action_delete_runs(self):

        pool = self.env.get('hr.payslip.run')
        ids = pool.search(
            [('register_id', 'in', ids)])
        pool.unlink()
        return True
