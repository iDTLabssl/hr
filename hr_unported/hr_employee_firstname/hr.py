# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2010 - 2014 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from openerp.osv import orm, fields
from openerp import models, fields, api


class hr_employee(orm.Model):
    _inherit = 'hr.employee'

    @api.model
    def init(self):
        cursor = self.env.cr
        cursor.execute('''\
SELECT id
FROM hr_employee
WHERE lastname IS NOT NULL
LIMIT 1''')
        if not cursor.fetchone():
            cursor.execute('''\
UPDATE hr_employee
SET lastname = name_related
WHERE name_related IS NOT NULL''')

    @api.model
    def create(self, vals):
        firstname = vals.get('firstname')
        lastname = vals.get('lastname')
        if firstname or lastname:
            names = (firstname, lastname)
            vals['name'] = " ".join(s for s in names if s)
        else:
            vals['lastname'] = vals['name']
        return super(hr_employee, self).create(
            vals)

    firstname = fields.Char("Firstname")
    lastname = fields.Char("Lastname", required=True)
