# -*- coding:utf-8 -*-
#
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
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
from openerp.tools.translate import _
from openerp import models, fields, api


class hr_department(orm.Model):

    _name = 'hr.department'
    _inherit = 'hr.department'

    code = fields.Char(
            'Code',
            size=64
        )
    sequence =  fields.Integer(
            'Sequence',
            select=True,
            help="Gives the sequence order when displaying a list of "
                 "departments."
        )
    parent_id = fields.Many2one(
            'hr.department',
            'Parent Department',
            select=True,
            ondelete='cascade'
        )
    parent_left = fields.Integer(
            'Left Parent',
            select=1
        )
    parent_right = fields.Integer(
            'Right Parent',
            select=1
        )

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'


    @api.model
    def _rec_message(self):
        return _('The code for the department must be unique per company!')

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', _rec_message),
    ]

    @api.model
    def name_get(self):
        """
        Show department code with name
        """
        context = self.env.context
        ids = self.search()

        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        return [
            (
                record.id,
                '[%s] %s' % (record.code, record.name)
                if record.code else record.name
            )
            for record in self.browse()
        ]

    @api.model
    def name_search(
            self,name='', args=None, operator='ilike',
            limit=100):
        if args is None:
            args = []
        ids = self.search(
            ['|', ('code', 'ilike', name), ('name', 'ilike', name)] + args,
            limit=limit
        )
        return self.name_get()
