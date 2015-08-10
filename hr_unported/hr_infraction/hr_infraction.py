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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp import models, fields, api


class hr_infraction_category(orm.Model):

    _name = 'hr.infraction.category'
    _description = 'Infraction Type'
    
    name = fields.Char(
            'Name',
            required=True
        )
    code = fields.Char(
            'Code',
            required=True
        )


class hr_infraction(orm.Model):

    _name = 'hr.infraction'
    _description = 'Infraction'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
      
    name = fields.Char(
            'Subject',
            size=256,
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]}
        )
    date = fields.Date(
            'Date',
            required=True,
            readonly=True,
            default = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            states={'draft': [('readonly', False)]}
        )
    employee_id = fields.Many2one(
            'hr.employee',
            'Employee',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]}
        )
    category_id = fields.Many2one(
            'hr.infraction.category',
            'Category',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
    action_ids = fields.One2many(
            'hr.infraction.action',
            'infraction_id',
            'Actions',
            readonly=True
        )
    memo = fields.Text(
            'Description',
            readonly=True,
            states={'draft': [('readonly', False)]}
        )
    state = fields.Selection(
            [
                ('draft', 'Draft'),
                ('confirm', 'Confirmed'),
                ('action', 'Actioned'),
                ('noaction', 'No Action'),
            ],
            'State',
            readonly=True,
            default = 'draft'
        )
    }
    
    _track = {
        'state': {
            'hr_infraction.mt_alert_infraction_confirmed': (
                lambda self, cr, u, obj, ctx=None: obj['state'] == 'confirm'),
            'hr_infraction.mt_alert_infraction_action': (
                lambda self, cr, u, obj, ctx=None: obj['state'] == 'action'),
            'hr_infraction.mt_alert_infraction_noaction': (
                lambda self, cr, u, obj, ctx=None: obj['state'] == 'noaction'),
        },
    }

    @api.model
    def _needaction_domain_get(self):
        users_obj = self.pool.get('res.users')
        domain = []
        if users_obj.has_group('base.group_hr_manager'):
            domain = [('state', '=', 'confirm')]
        if len(domain) == 0:
            return False
        return domain
    
    @api.multi
    def unlink(self):
        for infraction in self.browse():
            if infraction.state not in ['draft']:
                raise orm.except_orm(
                    _('Error'),
                    _('Infractions that have progressed beyond "Draft" state '
                      'may not be removed.')
                )
        return super(hr_infraction, self).unlink()

    @api.onchange('category_id') 
    def onchange_category(self,category_id):
        res = {'value': {'name': False}}
        if category_id:
            category = self.pool.get('hr.infraction.category').browse(
            category_id
            )
            res['value']['name'] = category.name
        return res

ACTION_TYPE_SELECTION = [
    ('warning_verbal', 'Verbal Warning'),
    ('warning_letter', 'Written Warning'),
    ('transfer', 'Transfer'),
    ('suspension', 'Suspension'),
    ('dismissal', 'Dismissal'),
]


class hr_infraction_action(orm.Model):

    _name = 'hr.infraction.action'
    _description = 'Action Based on Infraction'
        
    infraction_id = fields.Many2one(
            'hr.infraction',
            'Infraction',
            ondelete='cascade',
            required=True,
            readonly=True
        )
     type = fields.Selection(
            ACTION_TYPE_SELECTION,
            'Type',
            required=True
        )
     memo = fields.Text(
            'Notes'
        )
     employee_id = fields.Many2one(
            'Employee',
            'hr.employee',
            realted='infraction_id.employee_id',
            readonly=True
        )
     warning_id =  fields.Many2one(
            'hr.infraction.warning',
            'Warning',
            readonly=True
        )
     transfer_id = fields.Many2one(
            'hr.department.transfer',
            'Transfer',
            readonly=True
        )
    _rec_name = 'type'

    @api.multi
    def unlink(self):

        for action in self.browse():
            if action.infraction_id.state not in ['draft']:
                raise orm.except_orm(
                    _('Error'),
                    _('Actions belonging to Infractions not in "Draft" state '
                      'may not be removed.')
                )

        return super(hr_infraction_action, self).unlink(
        )


class hr_warning(orm.Model):

    _name = 'hr.infraction.warning'
    _description = 'Employee Warning'
        
    name = fields.Char(
            'Subject',
            size=256
        )
    date = fields.Date(
            'Date Issued',
           date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        )
    type = fields.Selection(
            [
                ('verbal', 'Verbal'),
                ('written', 'Written'),
            ],
            'Type',
            required=True,
            default = 'written'
        )
    action_id = fields.Many2one(
            'hr.infraction.action',
            'Action',
            ondelete='cascade',
            readonly=True
        )
     infraction_id = fields.Many2one(
            realted='action_id.infraction_id',
            obj='hr.infraction',
            string='Infraction',
            readonly=True
        )
     employee_id = fields.Many2one(
            related='infraction_id.employee_id',
            obj='hr.employee',
            string='Employee',
            readonly=True
        )


    @api.multi
    def unlink(self):
        for warning in self.browse():
            if (warning.action_id
                    and warning.action_id.infraction_id.state != 'draft'):
                raise orm.except_orm(
                    _('Error'),
                    _('Warnings attached to Infractions not in "Draft" state '
                      'may not be removed.')
                )
        return super(hr_warning, self).unlink(cr, uid, ids, context=context)


class hr_employee(orm.Model):

    _name = 'hr.employee'
    _inherit = 'hr.employee'
    infraction_ids = fields.One2many(
            'hr.infraction',
            'employee_id',
            'Infractions',
            readonly=True
        )
     infraction_action_ids = fields.One2many(
            'hr.infraction.action',
            'employee_id',
            'Disciplinary Actions',
            readonly=True
        )
