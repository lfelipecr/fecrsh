# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    expense_id = fields.Many2one('hr.expense',string='Gasto relacionado',copy=False)
    expense_sheet_id = fields.Many2one('hr.expense.sheet',string='Informe de Gasto',copy=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    in_expense_sheet = fields.Boolean(default=False, copy=False)
    invoice_id = fields.Many2one('account.move', copy=False)

