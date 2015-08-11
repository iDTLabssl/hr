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

from openerp.osv import orm


class hr_payslip(orm.Model):
    _inherit = 'hr.payslip'

    @api.model
    def compute_sheet(self):
        super(hr_payslip, self).compute_sheet(
        )
        self.compute_lines_ytd()

    @api.model
    def compute_lines_ytd(self):
        for payslip in self.browse():
            # Create a dict of the required lines that will be used
            # to sum amounts over the payslips
            line_dict = {
                line.salary_rule_id.code: 0 for line in payslip.line_ids}

            # Get the payslips of the employee for the current year
            date_from = payslip.date_from[0:4] + "-01-01"

            employee_payslip_ids = self.search(
                [
                    ('employee_id', '=', payslip.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<=', payslip.date_to),
                    ('state', '=', 'done'),
                ])

            employee_payslips = self.browse(
                employee_payslip_ids)

            # Iterate one time over each line of each payslip of the
            # employee since the beginning of the year and sum required
            # lines
            for emp_payslip in employee_payslips:
                is_refund = emp_payslip.credit_note and -1 or 1

                for line in emp_payslip.line_ids:
                    if line.salary_rule_id.code in line_dict:
                        line_dict[line.salary_rule_id.code] += \
                            line.total * is_refund

            # For each line in the payslip, write the related total ytd
            for line in payslip.line_ids:
                amount = line_dict[line.salary_rule_id.code] + line.total
                self.pool['hr.payslip.line'].write(
                    [line.id], {'total_ytd': amount})
