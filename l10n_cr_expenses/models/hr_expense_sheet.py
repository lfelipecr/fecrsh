# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero

from odoo.exceptions import ValidationError

TYPE_EXPENSE = [('expense','Gasto'),
                ('invoice','Factura Régimen Simplificado')]

class ExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    #modificado de original
    payment_mode = fields.Selection([
        ("own_account", "Employee (to reimburse)"),
        ("company_account", "Company")
    ], default='own_account', tracking=True, states={'draft': [('readonly', False)],
                                                     'done': [('readonly', True)],
                                                     'approved': [('readonly', True)],
                                                     'reported': [('readonly', True)]}, string="Pagado por")



    #Facturas de proveedor
    invoice_supplier_ids = fields.One2many('account.move','expense_sheet_id', copy=False)
    total_invoice = fields.Monetary('Total factura', compute='compute_invoice_supplier_totals',copy=False)




    @api.onchange('invoice_supplier_ids')
    def _onchange_invoice_supplier_ids(self):
        for record in self:
            record.compute_invoice_supplier_totals()

    @api.depends('invoice_supplier_ids','invoice_supplier_ids.state','invoice_supplier_ids.amount_total','invoice_supplier_ids.payment_state')
    def compute_invoice_supplier_totals(self):
        for record in self:
            t = 0.0
            if record.invoice_supplier_ids:
                for inv in record.invoice_supplier_ids:
                    t += abs(inv.amount_total_signed)
            record.total_invoice = t

    @api.depends('expense_line_ids.total_amount_company', 'total_invoice')
    def _compute_amount(self):
        for sheet in self:
            amount_expenses = sum(sheet.expense_line_ids.mapped('total_amount_company'))
            sheet.total_amount = amount_expenses + sheet.total_invoice


    def action_sheet_move_create(self):
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            if samples.count(False):
                raise UserError(_("You can't mix sample expenses and regular ones"))
            self.write({'state': 'post'})
            return

        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.company.currency_id).rounding))

        #movimiento para cada gasto
        res = expense_line_ids.action_move_create()

        #Nuevo 25-11-2021 ******************
        move_group_by_sheet = res
        self.action_move_invsupplier_create(move_group_by_sheet) #Generar asiento de contrapartida para las facturas relacionadas
        for move in move_group_by_sheet.values(): #Luego de generar los asientos pasan a publicarse
            move._post()

        #Fin 25-11-2021 ********************

        for sheet in self.filtered(lambda s: not s.accounting_date):
            sheet.accounting_date = sheet.account_move_id.date
        to_post = self.filtered(lambda sheet: sheet.payment_mode == 'own_account' and sheet.expense_line_ids)
        to_post.write({'state': 'post'})
        (self - to_post).write({'state': 'done'})
        self.activity_update()
        return res


    def action_move_invsupplier_create(self,move_group_by_sheet):
        if not move_group_by_sheet:
            move_group_by_sheet = self._get_account_move_by_sheet()

        invoice_supplier_ids = self.mapped('invoice_supplier_ids')
        if invoice_supplier_ids:
            for inv in invoice_supplier_ids:
                move = move_group_by_sheet[inv.expense_sheet_id.id]

                def _get_move_lines(inv):
                    mlines = [
                        (0, False, {'credit': abs(inv.amount_total_signed),
                                    'account_id': inv.expense_sheet_id.employee_id.address_home_id.property_account_payable_id.id,
                                    'in_expense_sheet': True, #Nuevo
                                    'invoice_id': inv.id, #Nuevo
                                    'partner_id': inv.partner_id.id,
                                    'name': 'Empleado: %s ' % (inv.expense_sheet_id.employee_id.name)}),
                        (0, False, {'debit': abs(inv.amount_total_signed),
                                    'account_id': inv.partner_id.property_account_payable_id.id,
                                    'in_expense_sheet': True, #Nuevo
                                    'invoice_id': inv.id, #Nuevo
                                    'partner_id': inv.expense_sheet_id.employee_id.address_home_id.id,
                                    'name': 'Factura: %s' % (inv.name)}),
                    ]
                    return mlines

                move_line_values = _get_move_lines(inv)

                move.write({'line_ids': move_line_values})

        return move_group_by_sheet




