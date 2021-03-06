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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import fields, orm
from openerp import models, fields, api


class hr_contract(orm.Model):

    _name = 'hr.contract'
    _inherit = ['hr.contract', 'mail.thread', 'ir.needaction_mixin']

    
    @api.depends('department_id')
    def _get_ids_from_employee(self):

        res = []
        employee_pool = self.env['hr.employee']
        for ee in employee_pool:
            for contract in ee.contract_ids:
                if contract.state not in ['pending_done', 'done']:
                    res.append(contract.id)
        return res

    @api.multi
    def _get_department(self):

        res = dict.fromkeys(ids, False)
        states = ['pending_done', 'done']
        for contract in self:
            if contract.department_id and contract.state in states:
                res[contract.id] = contract.department_id.id
            elif contract.employee_id.department_id:
                res[contract.id] = contract.employee_id.department_id.id
        return res

        state = fields.Selection(
            [
                ('draft', 'Draft'),
                ('trial', 'Trial'),
                ('trial_ending', 'Trial Period Ending'),
                ('open', 'Open'),
                ('contract_ending', 'Ending'),
                ('pending_done', 'Pending Termination'),
                ('done', 'Completed')
            ],
            'State',
            readonly=True,
            default = 'draft'
        )
        # store this field in the database and trigger a change only if the
        # contract is in the right state: we don't want future changes to an
        # employee's department to impact past contracts that have now ended.
        # Increased priority to override hr_simplify.
        department_id = fields.Many2one(
            string="Department",
            'hr.department',
            compute = '_get_department',
            readonly=True,
        )
        # At contract end this field will hold the job_id, and the
        # job_id field will be set to null so that modules that
        # reference job_id don't include deactivated employees.
        end_job_id = fields.Many2one(
            'hr.job',
            'Job Title',
            readonly=True,
        )
        # The following are redefined again to make them editable only in
        # certain states
        employee_id = fields.Many2one(
            'hr.employee',
            "Employee",
            required=True,
            readonly=True,
            states={
                'draft': [('readonly', False)]
            },
        )
        type_id = fields.Many2one(
            'hr.contract.type',
            "Contract Type",
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
        date_start = fields.Date(
            'Start Date',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
        wage = fields.Float(
            'Wage',
            digits=(16, 2),
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
            help="Basic Salary of the employee",
        )


    _track = {
        'state': {
            'hr_contract_state.mt_alert_trial_ending': (
                lambda s, cr, u, o, c=None: o['state'] == 'trial_ending'),
            'hr_contract_state.mt_alert_open': (
                lambda s, cr, u, o, c=None: o['state'] == 'open'),
            'hr_contract_state.mt_alert_contract_ending': (
                lambda s, cr, u, o, c=None: o['state'] == 'contract_ending'),
        },
    }

    def _needaction_domain_get(self):

        users_obj = self.env['res.users']
        domain = []

        if users_obj.has_group('base.group_hr_manager'):
            domain = [
                ('state', 'in', ['draft', 'contract_ending', 'trial_ending'])]
            return domain

        return False


# Revisit
#
    def onchange_job(self, cr, uid, ids, job_id, context=None):

        import logging
        _l = logging.getLogger(__name__)
        _l.warning('hr_contract_state: onchange_job()')
        res = False
        if isinstance(ids, (int, long)):
            ids = [ids]
        if ids:
            contract = self.browse(cr, uid, ids[0], context=None)
            if contract.state != 'draft':
                return res
        return super(hr_contract, self).onchange_job(
            cr, uid, ids, job_id, context=context
        )

    @api.multi
    def condition_trial_period(self):

        for contract in self:
            if not contract.trial_date_start:
                return False
        return True

    def try_signal_ending_contract(self):

        d = datetime.now().date() + relativedelta(days=+30)
        
        domain = [
                ('state', '','open'),('date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT)) ]
        res = self.search(domain)

        if len(res) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self:
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_ending_contract', cr
            )

    def try_signal_contract_completed(self):
        d = datetime.now().date()
        ids = self.search([
            ('state', '=', 'open'),
            ('date_end', '<', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ])
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_pending_done', cr
            )

    def try_signal_ending_trial(self):

        d = datetime.now().date() + relativedelta(days=+10)
        ids = self.search([
            ('state', '=', 'trial'),
            ('trial_date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ])
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_ending_trial', cr
            )

    def try_signal_open(self):

        d = datetime.now().date() + relativedelta(days=-5)
        ids = self.search([
            ('state', '=', 'trial_ending'),
            ('trial_date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ])
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_open', cr
            )

    def onchange_start(self):
        return {
            'value': {
                'trial_date_start': date_start,
            },
        }

    def state_trial(self):
        self.write({'state': 'trial'})
        return True

    def state_open(self):
        self.write({'state': 'open'})
        return True

    def state_pending_done(self):
        self.write({'state': 'pending_done'})
        return True

    def state_done(self):
        for i in ids:
            data = self.read(
                cr, uid, i, ['date_end', 'job_id'], context=context)
            vals = {'state': 'done',
                    'date_end': False,
                    'job_id': False,
                    'end_job_id': data['job_id'][0]}

            if data.get('date_end', False):
                vals['date_end'] = data['date_end']
            else:
                vals['date_end'] = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

            self.write(vals)
        return True
