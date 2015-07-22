# -*- coding:utf-8 -*-
#
#
#    Copyright (C) 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp import models, fields, api

EDUCATION_SELECTION = [
    ('none', 'No Education'),
    ('primary', 'Primary School'),
    ('secondary', 'Secondary School'),
    ('diploma', 'Diploma'),
    ('degree1', 'First Degree'),
    ('masters', 'Masters Degree'),
    ('phd', 'PhD'),
]


class hr_employee(orm.Model):

    _inherit = 'hr.employee'

    @api.one
    def _calculate_age(self):

        for ee in self:
            if ee.birthday:
                dBday = datetime.strptime(ee.birthday, OE_DFORMAT).date()
                dToday = datetime.now().date()
                self.age = (dToday - dBday).days / 365

    education = fields.Selection(EDUCATION_SELECTION, 'Education')
    age = fields.Integer('Age', compute='_calculate_age', readonly=True, store=False)
