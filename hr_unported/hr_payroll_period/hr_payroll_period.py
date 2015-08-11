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

import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import common_timezones, timezone, utc

from openerp import netsvc
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.osv import fields, orm
from openerp import models, fields, api


import logging
_logger = logging.getLogger(__name__)

# Obtained from: http://goo.gl/klh8p
#


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)


class hr_payroll_period(orm.Model):

    _name = 'hr.payroll.period'

    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char('Description', size=256, required=True)
    schedule_id = fields.Many2one(
            'hr.payroll.period.schedule', 'Payroll Period Schedule',
            required=True)
    date_start = fields.Datetime('Start Date', required=True)
    date_end = fields.Datetime('End Date', required=True)
    register_id = fields.Many2one(
            'hr.payroll.register', 'Payroll Register', readonly=True,
            states={'generate': [('readonly', False)]})
    state = fields.Selection([('open', 'Open'),
                                   ('ended', 'End of Period Processing'),
                                   ('locked', 'Locked'),
                                   ('generate', 'Generating Payslips'),
                                   ('payment', 'Payment'),
                                   ('closed', 'Closed')],
                                  'State', select=True, readonly=True,
                                   default = 'open')

    _order = "date_start, name desc"


    _track = {
        'state': {
            'hr_payroll_period.mt_state_open': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'open'),
            'hr_payroll_period.mt_state_end': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'ended'),
            'hr_payroll_period.mt_state_lock': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'locked'),
            'hr_payroll_period.mt_state_generate': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'generate'
            ),
            'hr_payroll_period.mt_state_payment': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'payment'
            ),
            'hr_payroll_period.mt_state_close': (
                lambda self, cr, uid, obj, ctx=None: obj['state'] == 'closed'),
        },
    }

    @api.model
    def _needaction_domain_get(self):

        users_obj = self.pool.get('res.users')
        domain = []

        if users_obj.has_group(cr, uid, 'hr_security.group_payroll_manager'):
            domain = [('state', 'not in', ['open', 'closed'])]
            return domain

        return False

    @api.model
    def is_ended(self, period_id):

        #
        # TODO - Someone who cares about DST should update this code
        # to handle it.
        #

        flag = False
        if period_id:
            utc_tz = timezone('UTC')
            utcDtNow = utc_tz.localize(datetime.now(), is_dst=False)
            period = self.browse(period_id)
            if period:
                dtEnd = datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
                utcDtEnd = utc_tz.localize(dtEnd, is_dst=False)
                if utcDtNow > utcDtEnd + timedelta(
                    minutes=(period.schedule_id.ot_max_rollover_hours * 60)
                ):
                    flag = True
        return flag

    @api.model
    def try_signal_end_period(self):
        """Method called, usually by cron, to transition any payroll periods
        that are past their end date.
        """

        #
        # TODO - Someone who cares about DST should update this code
        # to handle it.
        #

        utc_tz = timezone('UTC')
        utcDtNow = utc_tz.localize(datetime.now(), is_dst=False)
        period_ids = self.search([
            ('state', 'in', ['open']),
            ('date_end', '<=', utcDtNow.strftime(
                '%Y-%m-%d %H:%M:%S')),
        ])
        if len(period_ids) == 0:
            return

        wf_service = netsvc.LocalService('workflow')
        for pid in period_ids:
            wf_service.trg_validate(
            'hr.payroll.period', pid, 'end_period')

    @api.model
    def set_state_ended(self):

        #
        # TODO - Someone who cares about DST should update this code
        # to handle it.
        #

        wf_service = netsvc.LocalService('workflow')
        attendance_obj = self.pool.get('hr.attendance')
        detail_obj = self.pool.get('hr.schedule.detail')
        holiday_obj = self.pool.get('hr.holidays')
        for period in self.browse():
            utc_tz = timezone('UTC')
            dt = datetime.strptime(period.date_start, '%Y-%m-%d %H:%M:%S')
            utcDtStart = utc_tz.localize(dt, is_dst=False)
            dt = datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
            utcDtEnd = utc_tz.localize(dt, is_dst=False)
            if period.state in ['locked', 'generate']:
                for contract in period.schedule_id.contract_ids:
                    employee = contract.employee_id

                    # Unlock attendance
                    punch_ids = attendance_obj.search([
                        ('employee_id', '=', employee.id),
                        '&',
                        ('name', '>=', utcDtStart.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                        ('name', '<=', utcDtEnd.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                    ], order='name')
                    [wf_service.trg_validate(
                        'hr.attendance', pid, 'signal_unlock')
                     for pid in punch_ids]

                    # Unlock schedules
                    detail_ids = detail_obj.search([
                        ('schedule_id.employee_id', '=', employee.id),
                        '&',
                        ('date_start', '>=', utcDtStart.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                        ('date_start', '<=', utcDtEnd.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                    ], order='date_start')
                    [wf_service.trg_validate(
                        'hr.schedule.detail', did, 'signal_unlock')
                     for did in detail_ids]

                    # Unlock holidays/leaves that end in the current period
                    holiday_ids = holiday_obj.search([
                        ('employee_id', '=', employee.id),
                        '&',
                        ('date_to', '>=', utcDtStart.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                        ('date_to', '<=', utcDtEnd.strftime(
                            '%Y-%m-%d %H:%M:%S')),
                    ])
                    for hid in holiday_ids:
                        holiday_obj.write(
                        [hid], {
                                'payroll_period_state': 'unlocked'})

            self.write(period.id, {'state': 'ended'})

        return True

    @api.model
    def set_state_locked(self):

        #
        # TODO - Someone who cares about DST should update this code
        # to handle it.
        #

        wkf_service = netsvc.LocalService('workflow')
        attendance_obj = self.pool.get('hr.attendance')
        detail_obj = self.pool.get('hr.schedule.detail')
        holiday_obj = self.pool.get('hr.holidays')
        for period in self.browse():
            utc_tz = timezone('UTC')
            dt = datetime.strptime(period.date_start, '%Y-%m-%d %H:%M:%S')
            utcDtStart = utc_tz.localize(dt, is_dst=False)
            dt = datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
            utcDtEnd = utc_tz.localize(dt, is_dst=False)
            for contract in period.schedule_id.contract_ids:
                employee = contract.employee_id

                # Lock sign-in and sign-out attendance records
                punch_ids = attendance_obj.search([
                    ('employee_id', '=', employee.id),
                    '&',
                    ('name', '>=', utcDtStart.strftime('%Y-%m-%d %H:%M:%S')),
                    ('name', '<=', utcDtEnd.strftime(
                        '%Y-%m-%d %H:%M:%S')),
                ], order='name')
                for pid in punch_ids:
                    wkf_service.trg_validate(
                        'hr.attendance', pid, 'signal_lock')

                # Lock schedules
                detail_ids = detail_obj.search([
                    ('schedule_id.employee_id', '=', employee.id),
                    '&',
                    ('date_start', '>=', utcDtStart.strftime(
                        '%Y-%m-%d %H:%M:%S')),
                    ('date_start', '<=', utcDtEnd.strftime(
                        '%Y-%m-%d %H:%M:%S')),
                ], order='date_start')
                for did in detail_ids:
                    wkf_service.trg_validate(
                        'hr.schedule.detail', did, 'signal_lock')

                # Lock holidays/leaves that end in the current period
                holiday_ids = holiday_obj.search([
                    ('employee_id', '=', employee.id),
                    '&',
                    ('date_to', '>=', utcDtStart.strftime(
                        '%Y-%m-%d %H:%M:%S')),
                    ('date_to', '<=', utcDtEnd.strftime(
                        '%Y-%m-%d %H:%M:%S')),
                ])
                for hid in holiday_ids:
                    holiday_obj.write(
                        [hid], {'payroll_period_state': 'locked'})

            self.write(period.id, {
                       'state': 'locked'})

        return True

    @api.one
    def set_state_closed(self):

        return self.write({'state': 'closed'})


class hr_payperiod_schedule(orm.Model):

    _name = 'hr.payroll.period.schedule'

    @api.model
    def _tz_list(self):

        res = tuple()
        for name in common_timezones:
            res += ((name, name),)
        return res

    name = fields.Char('Description', size=256, required=True)
    tz = fields.Selection(_tz_list, 'Time Zone', required=True)
    paydate_biz_day = fields.Boolean('Pay Date on a Business Day')
    ot_week_startday = fields.Selection([
            ('0', _('Sunday')),
            ('1', _('Monday')),
            ('2', _('Tuesday')),
            ('3', _('Wednesday')),
            ('4', _('Thursday')),
            ('5', _('Friday')),
            ('6', _('Saturday')),
        ],
            'Start of Week', required=True, default = 1)
    ot_max_rollover_hours = fields.Integer(
            'OT Max. Continuous Hours', required=True,
            default = 6)
    ot_max_rollover_gap = fields.Integer(
            'OT Max. Continuous Hours Gap (in Min.)', required=True,
            default = 60)
    type = fields.Selection([
            ('manual', 'Manual'),
            ('monthly', 'Monthly'),
        ],
            'Type', required=True,
            default = 'monthly')
    mo_firstday = fields.Selection([
            ('1', '1'), ('2', '2'), ('3', '3'), (
                '4', '4'), ('5', '5'), ('6', '6'), ('7', '7'),
            ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), (
                '12', '12'), ('13', '13'), ('14', '14'),
            ('15', '15'), ('16', '16'), ('17', '17'), (
                '18', '18'), ('19', '19'), ('20', '20'), ('21', '21'),
            ('22', '22'), ('23', '23'), ('24', '24'), (
                '25', '25'), ('26', '26'), ('27', '27'), ('28', '28'),
            ('29', '29'), (
                '30', '30'), ('31', '31'),
        ],
            'Start Day', default = 1)
    mo_paydate = fields.Selection([
            ('1', '1'), ('2', '2'), ('3', '3'), (
                '4', '4'), ('5', '5'), ('6', '6'), ('7', '7'),
            ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), (
                '12', '12'), ('13', '13'), ('14', '14'),
            ('15', '15'), ('16', '16'), ('17', '17'), (
                '18', '18'), ('19', '19'), ('20', '20'), ('21', '21'),
            ('22', '22'), ('23', '23'), ('24', '24'), (
                '25', '25'), ('26', '26'), ('27', '27'), ('28', '28'),
            ('29', '29'), (
                '30', '30'), ('31', '31'),
        ],
            'Pay Date', default =3)
    contract_ids = fields.One2many('hr.contract', 'pps_id', 'Contracts')
    pay_period_ids = fields.One2many(
            'hr.payroll.period', 'schedule_id', 'Pay Periods')
    initial_period_date = fields.Date('Initial Period Start Date')
    active = fields.Boolean('Active', default = True)

    @api.multi
    def _check_initial_date(self):

        for obj in self.browse():
            if obj.type in ['monthly'] and not obj.initial_period_date:
                return False

        return True

    _constraints = [
        (_check_initial_date,
         'You must supply an Initial Period Start Date', ['type']),
    ]

    @api.model
    def add_pay_period(self):

        def get_period_year(dt):

            month_number = 0
            year_number = 0
            if dt.day < 15:
                month_number = dt.month
                year_number = dt.year
            else:
                dtTmp = add_months(dt, 1)
                month_number = dtTmp.month
                year_number = dtTmp.year
            return month_number, year_number

        #
        # XXX - Someone who cares about DST should update this code
        # to handle it.
        #

        schedule_obj = self.pool.get('hr.payroll.period.schedule')

        data = None
        for sched in schedule_obj.browse():
            local_tz = timezone(sched.tz)
            try:
                latest = max(
                    datetime.strptime(p.date_end, '%Y-%m-%d %H:%M:%S')
                    for p in sched.pay_period_ids
                )
            except ValueError:
                latest = False

            if not latest:
                # No pay periods have been defined yet for this pay period
                # schedule.
                if sched.type == 'monthly':
                    dtStart = datetime.strptime(
                        sched.initial_period_date, '%Y-%m-%d')
                    if dtStart.day > int(sched.mo_firstday):
                        dtStart = add_months(dtStart, 1)
                        dtStart = datetime(
                            dtStart.year, dtStart.month,
                            int(sched.mo_firstday), 0, 0, 0)
                    elif dtStart.day < int(sched.mo_firstday):
                        dtStart = datetime(
                            dtStart.year, dtStart.month,
                            int(sched.mo_firstday), 0, 0, 0)
                    else:
                        dtStart = datetime(
                            dtStart.year, dtStart.month, dtStart.day, 0, 0, 0)
                    dtEnd = add_months(dtStart, 1) - timedelta(days=1)
                    dtEnd = datetime(
                        dtEnd.year, dtEnd.month, dtEnd.day, 23, 59, 59)
                    month_number, year_number = get_period_year(dtStart)

                    # Convert from time zone of punches to UTC for storage
                    utcStart = local_tz.localize(dtStart, is_dst=None)
                    utcStart = utcStart.astimezone(utc)
                    utcEnd = local_tz.localize(dtEnd, is_dst=None)
                    utcEnd = utcEnd.astimezone(utc)

                    data = {
                        'name': 'Pay Period ' + str(
                            month_number) + '/' + str(year_number),
                        'schedule_id': sched.id,
                        'date_start': utcStart.strftime('%Y-%m-%d %H:%M:%S'),
                        'date_end': utcEnd.strftime('%Y-%m-%d %H:%M:%S'),
                    }
            else:
                if sched.type == 'monthly':
                    # Convert from UTC to timezone of punches
                    utcStart = datetime.strptime(
                        latest.date_end, '%Y-%m-%d %H:%M:%S')
                    utc_tz = timezone('UTC')
                    utcStart = utc_tz.localize(utcStart, is_dst=None)
                    utcStart += timedelta(seconds=1)
                    dtStart = utcStart.astimezone(local_tz)

                    # Roll forward to the next pay period start and end times
                    dtEnd = add_months(dtStart, 1) - timedelta(days=1)
                    dtEnd = datetime(
                        dtEnd.year, dtEnd.month, dtEnd.day, 23, 59, 59)
                    month_number, year_number = get_period_year(dtStart)

                    # Convert from time zone of punches to UTC for storage
                    utcStart = dtStart.astimezone(utc_tz)
                    utcEnd = local_tz.localize(dtEnd, is_dst=None)
                    utcEnd = utcEnd.astimezone(utc)

                    data = {
                        'name': 'Pay Period ' + str(
                            month_number) + '/' + str(year_number),
                        'schedule_id': sched.id,
                        'date_start': utcStart.strftime('%Y-%m-%d %H:%M:%S'),
                        'date_end': utcEnd.strftime('%Y-%m-%d %H:%M:%S'),
                    }
            if data is not None:
                schedule_obj.write(
                    sched.id,
                    {'pay_period_ids': [(0, 0, data)]})

    @api.multi
    def _get_latest_period(self,sched_id):

        sched = self.browse(sched_id)
        try:
            latest_period = max(
                datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
                for period in sched.pay_period_ids
            )
        except ValueError:
            latest_period = False
        return latest_period

    @api.model
    def try_create_new_period(self):
        """Try and create pay periods for up to 3 months from now."""

        #
        # TODO - Someone who cares about DST should update this code
        # to handle it.
        #

        dtNow = datetime.now()
        utc_tz = timezone('UTC')
        sched_obj = self.pool.get('hr.payroll.period.schedule')
        sched_ids = sched_obj.search([])
        for sched in sched_obj.browse(sched_ids):
            if sched.type == 'monthly':
                firstday = sched.mo_firstday
            else:
                continue
            dtNow = datetime.strptime(
                dtNow.strftime(
                    '%Y-%m-' + firstday + ' 00:00:00'), '%Y-%m-%d %H:%M:%S')
            loclDTNow = timezone(sched.tz).localize(dtNow, is_dst=False)
            utcDTFuture = loclDTNow.astimezone(
                utc_tz) + relativedelta(months=+3)

            if not sched.pay_period_ids:
                self.add_pay_period([sched.id])

            latest_period = self._get_latest_period(
                sched.id)
            utcDTStart = utc_tz.localize(
                datetime.strptime(
                    latest_period.date_start, '%Y-%m-%d %H:%M:%S'),
                is_dst=False)
            while utcDTFuture > utcDTStart:
                self.add_pay_period([sched.id])
                latest_period = self._get_latest_period(
                    sched.id)
                utcDTStart = utc_tz.localize(
                    datetime.strptime(
                        latest_period.date_start, '%Y-%m-%d %H:%M:%S'
                    ),
                    is_dst=False)


class contract_init(orm.Model):

    _inherit = 'hr.contract.init'

    pay_sched_id = fields.Many2one(
            'hr.payroll.period.schedule', 'Payroll Period Schedule',
            readonly=True, states={'draft': [('readonly', False)]})


class hr_contract(orm.Model):

    _name = 'hr.contract'
    _inherit = 'hr.contract'

    pps_id = fields.Many2one(
            'hr.payroll.period.schedule', 'Payroll Period Schedule',
            required=True,
            default = '_get_pay_sched')

    @api.model
    def _get_pay_sched(self):

        res = False
        init = self.get_latest_initial_values()
        if init is not None and init.pay_sched_id:
            res = init.pay_sched_id.id
        return res



class hr_payslip(orm.Model):

    _name = 'hr.payslip'
    _inherit = 'hr.payslip'

    exception_ids = fields.One2many('hr.payslip.exception', 'slip_id',
                                         'Exceptions', readonly=True)

    @api.model
    def compute_sheet(self):

        super(hr_payslip, self).compute_sheet()

        class BrowsableObject(object):

            def __init__(self, employee_id, dict):
                #self.pool = pool
                #self.cr = cr
                #self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):

            """a class that will be used into the python code, mainly for
            usability purposes"""

            @api.model
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute(
                    "SELECT sum(amount) as sum"
                    "FROM hr_payslip as hp, hr_payslip_input as pi "
                    "WHERE hp.employee_id = %s AND hp.state = 'done' "
                    "AND hp.date_from >= %s AND hp.date_to <= %s "
                    "AND hp.id = pi.payslip_id AND pi.code = %s",
                    (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()[0]
                return res or 0.0

        class WorkedDays(BrowsableObject):

            """a class that will be used into the python code, mainly
            for usability purposes"""

            @api.model
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute(
                    "SELECT sum(number_of_days) as number_of_days, "
                    "sum(number_of_hours) as number_of_hours"
                    "FROM hr_payslip as hp, hr_payslip_worked_days as pi "
                    "WHERE hp.employee_id = %s AND hp.state = 'done'"
                    "AND hp.date_from >= %s AND hp.date_to <= %s "
                    "AND hp.id = pi.payslip_id AND pi.code = %s",
                    (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            @api.model
            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            @api.model
            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):

            """a class that will be used into the python code, mainly for
            usability purposes"""

            @api.model
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute(
                    "SELECT sum(case when hp.credit_note = False then "
                    "(pl.total) else (-pl.total) end)"
                    "FROM hr_payslip as hp, hr_payslip_line as pl "
                    "WHERE hp.employee_id = %s AND hp.state = 'done' "
                    "AND hp.date_from >= %s AND hp.date_to <= %s "
                    "AND hp.id = pl.slip_id AND pl.code = %s",
                    (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        rule_obj = self.pool.get('hr.payslip.exception.rule')
        rule_ids = rule_obj.search(
            [('active', '=', True)])
        rule_seq = []
        for i in rule_ids:
            data = rule_obj.read(i, ['sequence'])
            rule_seq.append((i, data['sequence']))
        sorted_rule_ids = [
            id for id, sequence in sorted(rule_seq, key=lambda x:x[1])]

        for payslip in self.browse():
            payslip_obj = Payslips(
                self.pool,payslip.employee_id.id, payslip)

            codes = []
            categories = {}
            for line in payslip.details_by_salary_rule_category:
                if line.code not in codes:
                    categories[line.code] = line
                    codes.append(line.code)
            categories_obj = BrowsableObject(
                self.pool, payslip.employee_id.id, categories)

            worked_days = {}
            for line in payslip.worked_days_line_ids:
                worked_days[line.code] = line
            worked_days_obj = WorkedDays(
                self.pool, payslip.employee_id.id, worked_days)

            inputs = {}
            for line in payslip.input_line_ids:
                inputs[line.code] = line
            input_obj = InputLine(
                self.pool, payslip.employee_id.id, inputs)

            temp_dict = {}
            utils_dict = self.get_utilities_dict(
                payslip.contract_id, payslip, context=context)
            for k, v in utils_dict.iteritems():
                k_obj = BrowsableObject(
                    self.pool, payslip.employee_id.id, v)
                temp_dict.update({k: k_obj})
            utils_obj = BrowsableObject(
                self.pool,payslip.employee_id.id, temp_dict)

            localdict = {
                'categories': categories_obj,
                'payslip': payslip_obj,
                'worked_days': worked_days_obj,
                'inputs': input_obj,
                'utils': utils_obj,
                'result': None,
            }

            for rule in rule_obj.browse(
                sorted_rule_ids
            ):
                if rule_obj.satisfy_condition(
                    rule.id, localdict
                ):
                    val = {
                        'name': rule.name,
                        'slip_id': payslip.id,
                        'rule_id': rule.id,
                    }
                    self.pool.get('hr.payslip.exception').create(
                        val)

        return True


class hr_payslip_exception(orm.Model):

    _name = 'hr.payslip.exception'
    _description = 'Payroll Exception'

    name = fields.Char('Name', size=256, required=True, readonly=True)
    rule_id = fields.Many2one(
            'hr.payslip.exception.rule', 'Rule', ondelete='cascade',
            readonly=True)
    slip_id = fields.Many2one(
            'hr.payslip', 'Pay Slip', ondelete='cascade', readonly=True)
    severity = fields.Char(
            string="Severity", related="rule_id.severity", store=True,
            readonly=True)

# This is almost 100% lifted from hr_payroll/hr.salary.rule
# I omitted the parts I don't use.
#


class hr_payslip_exception_rule(orm.Model):

    _name = 'hr.payslip.exception.rule'
    _description = 'Rules describing pay slips in an abnormal state'

    name = fields.Char('Name', size=256, required=True)
    code = fields.Char('Code', size=64, required=True)
    sequence = fields.Integer(
            'Sequence', required=True,
            help='Use to arrange calculation sequence', select=True,
            default = 5)
    active = fields.Boolean(
            'Active',
            help="If the active field is set to false, it will allow you to "
                 "hide the rule without removing it.",
            default = True
        )
    company_id = fields.Many2one('res.company', 'Company',
            default = '_company_default_get')
    condition_select = fields.Selection(
            [
                ('none', 'Always True'),
                ('python', 'Python Expression')
            ],
            "Condition Based on",
            required=True,
            default = 'none'
        )
    condition_python = fields.Text(
            'Python Condition',
            readonly=False,
            help='The condition that triggers the exception.',
            default = "'"
        )
    severity = fields.Selection((
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ), 'Severity', required=True,
            default = 'low')
    note = fields.Text('Description')
    

# Available variables:
#----------------------
# payslip: object containing the payslips
# contract: hr.contract object
# categories: object containing the computed salary rule categories
#              (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs

# Note: returned value have to be set in the variable 'result'

    result = categories.GROSS.amount > categories.NET.amount"'"

    def satisfy_condition(self,rule_id, localdict):
        """
        @param rule_id: id of hr.payslip.exception.rule to be tested
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the
        given contract.
        Return False otherwise.
        """
        rule = self.browse(rule_id)

        if rule.condition_select == 'none':
            return True
        else:  # python code
            try:
                eval(rule.condition_python,
                     localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise orm.except_orm(
                    _('Error!'),
                    _('Wrong python condition defined for payroll exception '
                      'rule %s (%s).') % (rule.name, rule.code))


class hr_payslip_amendment(orm.Model):

    _name = 'hr.payslip.amendment'
    _inherit = 'hr.payslip.amendment'

    pay_period_id = fields.Many2one(
            'hr.payroll.period', 'Pay Period',
            domain=[('state', 'in', ['open', 'ended', 'locked', 'generate'])],
            required=False,
            readonly=True,
            states={
                'draft': [('readonly', False)],
                'validate': [('required', True)],
                'done': [('required', True)]
            }
        )


class hr_holidays_status(orm.Model):

    _name = 'hr.holidays.status'
    _inherit = 'hr.holidays.status'

    code = fields.Char('Code', size=16, required=True)

    _sql_constraints = [(
        'code_unique', 'UNIQUE(code)',
        'Codes for leave types must be unique!')]


class hr_holidays(orm.Model):

    _name = 'hr.holidays'
    _inherit = 'hr.holidays'

    payroll_period_state = fields.Selection(
            [('unlocked', 'Unlocked'), ('locked', 'Locked')],
            'Payroll Period State', readonly=True,
            defualt = 'unlocked')

    @api.multi
    def unlink(self):
        for h in self.browse():
            if h.payroll_period_state == 'locked':
                raise orm.except_orm(
                    _('Warning!'),
                    _('You cannot delete a leave which belongs to a payroll '
                      'period that has been locked.')
                )
        return super(hr_holidays, self).unlink()

    @api.model
    def write(self, vals):
        for h in self.browse():
            if h.payroll_period_state == 'locked' and not vals.get(
                'payroll_period_state', False
            ):
                raise orm.except_orm(
                    _('Warning!'),
                    _('You cannot modify a leave which belongs to a payroll '
                      'period that has been locked.')
                )
        return super(hr_holidays, self).write(vals)
