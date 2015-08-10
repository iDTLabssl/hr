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

from openerp import netsvc
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _


class hr_employee(orm.Model):

    _name = 'hr.employee'
    _inherit = 'hr.employee'

        # 'state' is already being used by hr_attendance
        status = fields.Selection(
            [
                ('new', 'New-Hire'),
                ('onboarding', 'On-Boarding'),
                ('active', 'Active'),
                ('pending_inactive', 'Pending Deactivation'),
                ('inactive', 'Inactive'),
                ('reactivated', 'Re-Activated'),
            ],
            'Status',
            readonly=True, defult='new',
        )
        
        inactive_ids = fields.One2many(
            'hr.employee.termination',
            'employee_id',
            'Deactivation Records',
        )
        
        saved_department_id = fields.Many2one(
            'hr.department',
            'Saved Department',
        )
    

    @api.one
    def condition_finished_onboarding(self):
        #employee = self.browse(cr, uid, ids[0], context=context)
        return self.status == 'onboarding'


    #
    # Need to revisit this
    #
    @api.model
    def state_active(self):
        ids = self.ids
        if isinstance(ids, (int, long)):
            ids = [ids]
       

        data = self.read(
            ['status', 'saved_department_id']
        )
        for d in data:
            if d.get('status') == 'pending_inactive':
                if d.get('saved_department_id'):
                    department_id = d['saved_department_id'][0]
                else:
                    department_id = False
                self.write(
                    ['id'], {
                        'status': 'active',
                        'department_id': department_id,
                        'saved_department_id': False,
                    })
            else:
                self.write( {'status': 'active'})

        return True

    @api.model
    def state_pending_inactive(self):
        ids = self.ids
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        data = self.read(['department_id'])
        for d in data:
            if d.get('department_id'):
                saved_department_id = d['department_id'][0]
            else:
                saved_department_id = False
            self.write(d['id'], {
                'status': 'pending_inactive',
                'saved_department_id': saved_department_id,
                'department_id': False,
            })
        return True

            ids = [ids]
        data = self.read(
            ['status', 'saved_department_id']
        )
        for d in data:
            vals = {
                'active': False,
                'status': 'inactive',
                'job_id': False,
            }
            if d['status'] and d['status'] == 'pending_inactive':
                if d.get('saved_department_id'):
                    department_id = d['saved_department_id'][0]
                else:
                    department_id = False
                vals.update({
                    'department_id': department_id,
                    'saved_department_id': False,
                })

            self.pool.get('hr.employee').write(
                d['id'], vals)
        return True
    
    @api.model
    def signal_reactivate(self):
        for employee in self.browse():
            cr = self.env.cr
            uid =self.env.uid

            self.write(employee.id, {'active': True})
            netsvc.LocalService('workflow').trg_validate(
                uid, 'hr.employee', employee.id, 'signal_reactivate', cr)
        return True


class hr_employee_termination_reason(orm.Model):

    _name = 'hr.employee.termination.reason'
    _description = 'Reason for Employment Termination'

        name = fields.Char(
            'Name',
            size=256,
            required=True
        )

class hr_employee_termination(orm.Model):

    _name = 'hr.employee.termination'
    _description = 'Data Related to Deactivation of Employee'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        name = fields.Date(
            'Effective Date',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
        reason_id = fields.Many2one(
            'hr.employee.termination.reason',
            'Reason',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
        notes = fields.Text(
            'Notes',
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
        employee_id = fields.Many2one(
            'hr.employee',
            'Employee',
            required=True,
            readonly=True,
        )
        department_id = fields.Integer(
            string="Department",
            related='employee_id.department_id',
            store=True,
        )
        saved_department_id = fields.Integer(
            string="Department",
            related='employee_id.saveddepartment_id',
            store=True,
        ),
        state = fields.Selection(
            [
                ('draft', 'Draft'),
                ('confirm', 'Confirmed'),
                ('cancel', 'Cancelled'),
                ('done', 'Done'),
            ],
            'State',
            readonly=True,
            deafualt = 'draft'
        ),


    _track = {
        'state': {
            'hr_employee_state.mt_alert_state_confirm': (
                lambda s, c, u, obj, ctx=None: obj['state'] == 'confirm'),
            'hr_employee_state.mt_alert_state_done': (
                lambda s, c, u, obj, ctx=None: obj['state'] == 'done'),
            'hr_employee_state.mt_alert_state_cancel': (
                lambda s, c, u, obj, ctx=None: obj['state'] == 'cancel'),
        },
    }


    @api.model
    def _needaction_domain_get(self):

        users_obj = self.pool.get('res.users')
        domain = []

        if users_obj.has_group('base.group_hr_user'):
            domain = [('state', 'in', ['draft'])]

        if users_obj.has_group('base.group_hr_manager'):
            if len(domain) > 0:
                domain = ['|'] + domain + [('state', '=', 'confirm')]
            else:
                domain = [('state', '=', 'confirm')]

        if len(domain) > 0:
            return domain

        return False

    @api.model
    def unlink(self):
        for term in self.browse():
            if term.state not in ['draft']:
                raise orm.except_orm(
                    _('Unable to delete record!'),
                    _('Employment termination already in progress. Use the '
                      '"Cancel" button instead.'))
            # Trigger employee status change back to Active and contract back
            # to Open
            wkf = netsvc.LocalService('workflow')
            wkf.trg_validate(
                'hr.employee', term.employee_id.id, 'signal_active')
            for contract in term.employee_id.contract_ids:
                if contract.state == 'pending_done':
                    wkf.trg_validate(
                        'hr.contract', contract.id, 'signal_open')

        return super(hr_employee_termination, self).unlink(
        )

    @api.model
    def effective_date_in_future(self):

        today = datetime.now().date()
        for term in self.browse():
            effective_date = datetime.strptime(
                term.name, DEFAULT_SERVER_DATE_FORMAT).date()
            if effective_date <= today:
                return False

        return True

    @api.model
    def state_cancel(self):

        ids = self.ids
        if isinstance(ids, (int, long)):
            ids = [ids]

        for term in self.browse():

            # Trigger a status change of the employee and his contract(s)
            wkf = netsvc.LocalService('workflow')
            wkf.trg_validate(
                'hr.employee', term.employee_id.id, 'signal_active')
            for contract in term.employee_id.contract_ids:
                if contract.state == 'pending_done':
                    wkf.trg_validate(
                        'hr.contract', contract.id, 'signal_open')

            self.write(term.id, {'state': 'cancel'})

        return True

    @api.model
    def state_done(self):

        for term in self.browse():
            if self.effective_date_in_future(
                    cr, uid, [term.id], context=context):
                raise orm.except_orm(
                    _('Unable to deactivate employee!'),
                    _('Effective date is still in the future.')
                )

            # Trigger a status change of the employee and any contracts pending
            # termination.
            wkf = netsvc.LocalService('workflow')
            for contract in term.employee_id.contract_ids:
                if contract.state == 'pending_done':
                    wkf.trg_validate(
                        'hr.contract', contract.id, 'signal_done'
                    )
            wkf.trg_validate(
                'hr.employee', term.employee_id.id, 'signal_inactive'
            )

            self.write(term.id, {'state': 'done'})

        return True


class hr_contract(orm.Model):

    _name = 'hr.contract'
    _inherit = 'hr.contract'

    def end_contract(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]

        if len(ids) == 0:
            return False

        context.update({'end_contract_id': ids[0]})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.contract.end',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    @api.model
    def _state_common(self):

        wkf = netsvc.LocalService('workflow')
        for contract in self.browse():
            if contract.employee_id.status == 'new':
                wkf.trg_validate(
                    'hr.employee', contract.employee_id.id,
                    'signal_confirm'
                )

    @api.model
    def state_trial(self):
        """Override 'trial' contract state to also change employee
        state: new -> onboarding
        """

        res = super(hr_contract, self).state_trial(
        )
        self._state_common()
        return res

    @api.model
    def state_open(self):
        """Override 'open' contract state to also change employee
        state: new -> onboarding
        """

        res = super(hr_contract, self).state_open(
        )
        self._state_common()
        return res

    @api.model
    def try_signal_contract_completed(self):

        d = datetime.now().date()
        ids = self.search([
            ('state', '=', 'open'),
            ('date_end', '<', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ])
        if len(ids) == 0:
            return

        for c in self.browse():
            vals = {
                'name': c.date_end or time.strftime(
                    DEFAULT_SERVER_DATE_FORMAT
                ),
                'employee_id': c.employee_id.id,
                'reason': 'contract_end',
            }
            self.setup_pending_done(c, vals)

    @api.model
    def setup_pending_done(self, contract, term_vals):
        """Start employee deactivation process."""

        term_obj = self.pool.get('hr.employee.termination')
        dToday = datetime.now().date()

        # If employee is already inactive simply end the contract
        wkf = netsvc.LocalService('workflow')
        if not contract.employee_id.active:
            wkf.trg_validate(
                'hr.contract', contract.id, 'signal_done')
            return

        # Ensure there are not other open contracts
        #
        open_contract = False
        ee = self.pool.get('hr.employee').browse(
            contract.employee_id.id)
        for c2 in ee.contract_ids:
            if c2.id == contract.id or c2.state == 'draft':
                continue
            if ((not c2.date_end or datetime.strptime(
                    c2.date_end,
                    DEFAULT_SERVER_DATE_FORMAT).date() >= dToday
                 )and c2.state != 'done'):
                open_contract = True

        # Don't create an employment termination if the employee has an open
        # contract or if this contract is already in the 'done' state.
        if open_contract or contract.state == 'done':
            return

        # Also skip creating an employment termination if there is already one
        # in progress for this employee.
        term_ids = term_obj.search(
            [
                ('employee_id', '=', contract.employee_id.id),
                ('state', 'in', ['draft', 'confirm'])
            ])
        if len(term_ids) > 0:
            return

        term_obj.create(term_vals)

        # Set the contract state to pending completion
        wkf = netsvc.LocalService('workflow')
        wkf.trg_validate(
            'hr.contract', contract.id, 'signal_pending_done'
        )

        # Set employee state to pending deactivation
        wkf.trg_validate(
            'hr.employee', contract.employee_id.id,
            'signal_pending_inactive'
        )


class hr_job(orm.Model):

    _name = 'hr.job'
    _inherit = 'hr.job'

    # Override calculation of number of employees in job. Remove employees for
    # which the termination process has already started.
    #
    
    @api.model
    def _no_of_employee(self,name, args):
        res = {}
        count = 0
        for job in self.browse():
            count = len(
                ee for ee in job.employee_ids
                if ee.active and ee.status != 'pending_inactive'
            )
            res[job.id] = {
                'no_of_employee': count,
                'expected_employees': count + job.no_of_recruitment,
            }
        return res


    #@api.one
    #@api.depends('no_of_recruitment')
    def _get_job_position(self):
        data = self.pool.get('hr.employee').read(
            ['job_id']
        )
        return [d['job_id'][0] for d in data if d['job_id']]

    _columns = {
        # Override from base class. Also, watch 'status' field of hr.employee
        'no_of_employee': fields.function(
            _no_of_employee,
            string="Current Number of Employees",
            help='Number of employees currently occupying this job position.',
            store={
                'hr.employee': (_get_job_position, ['job_id', 'status'], 10),
            },
            multi='no_of_employee',
        ),
        'expected_employees': fields.function(
            _no_of_employee,
            string='Total Forecasted Employees',
            help='Expected number of employees for this job position after '
                 'new recruitment.',
            store={
                'hr.job': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['no_of_recruitment'],
                    10
                ),
                'hr.employee': (_get_job_position, ['job_id', 'status'], 10),
            },
            multi='no_of_employee',
        ),
    }
# -*- coding:utf-8 -*-
#
