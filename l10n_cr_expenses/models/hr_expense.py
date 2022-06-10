# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TYPE_EXPENSE = [('expense','Gasto'),
                ('invoice','Factura Régimen Simplificado')]

class Expense(models.Model):
    _inherit = "hr.expense"

    invoice_id = fields.Many2one('account.move',string='Factura de proveedor', store=True, readonly=True,copy=False)
    type_expense = fields.Selection(selection=TYPE_EXPENSE, string='Tipo', store=True, default='expense', copy=False)
    supplier_id = fields.Many2one('res.partner', string='Proveedor', copy=False)

    # def action_submit_expenses(self):
    #     res = super(Expense, self).action_submit_expenses()
    #     if self.type_expense == 'invoice':
    #         self._create_invoide_supplier()
    #     return res

    # @api.model
    # def create(self, vals):
    #     super(Expense, self).create(vals)
    #     self._create_invoide_supplier(vals)


    # def write(self,values):
    #     self._create_invoide_supplier()
    #     return super(Expense, self).write(values)


    def create_invoice_supplier(self):
        if self.type_expense == 'invoice':
            if not self.supplier_id:
                raise ValidationError(_("Debe seleccionar al proveedor."))

            if not self.date:
                raise ValidationError(_("Debe ingresar la fecha de gasto."))

            if not self.account_id:
                raise ValidationError(_("Debe seleccionar la cuenta de gasto."))

            if not self.tax_ids:
                raise ValidationError(_("Debe seleccionar al menos un impuesto."))


            values = {
                'expense_id': self.id ,# New add
                'move_type': 'in_invoice',
                'tipo_documento': 'FEC',
                'date_issuance': self.date,
                'invoice_date': self.date,
                'date': self.date,
                'currency_id': self.currency_id.id,
                'partner_id': self.supplier_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': self.product_id.name,
                    'price_unit': self.unit_amount,
                    'product_id': self.product_id.id,
                    'quantity': self.quantity,
                    'account_id': self.account_id.id,
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                    'tax_ids': [(6, 0, self.tax_ids.ids)],
                })],

            }

            if self.invoice_id:
                if self.invoice_id == 'draft':
                    self.invoice_id.write(values)
            else:
                move = self.env['account.move'].sudo().create(values)
                #move.action_post()
                if move:
                    self.invoice_id = move
                    self.reference = move.name



    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)

            # link move lines to move, and move to expense sheet
            move.write({'line_ids': [(0, 0, line) for line in move_line_values]})
            expense.sheet_id.write({'account_move_id': move.id})

            if expense.payment_mode == 'company_account':
                expense.sheet_id.paid_expense_sheets()

        # for move in move_group_by_sheet.values():
        #     move._post()

        return move_group_by_sheet
