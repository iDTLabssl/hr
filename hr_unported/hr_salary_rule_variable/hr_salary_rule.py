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


class hr_salary_rule(orm.Model):
    _inherit = 'hr.salary.rule'
       
    variable_ids = fields.One2many(
            'hr.salary.rule.variable',
            'salary_rule_id',
            'Variables'
        )

    # Rewrite compute_rule (from hr_payroll module)
    # so that the python script in the rule may reference the rule itself
    def compute_rule(self,rule_id, localdict):

        # Add reference to the rule
        localdict['rule_id'] = rule_id

        return super(hr_salary_rule, self).compute_rule(
            rule_id, localdict
        )
