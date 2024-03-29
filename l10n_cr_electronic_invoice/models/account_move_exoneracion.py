# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import pytz


class AccountInvoice(models.Model):
    _inherit = "account.move"

    check_exoneration = fields.Boolean(string='Exonerar', default = False)
    vat = fields.Char('Identificación')
    tip_doc = fields.Many2one('aut.ex', string='Tipo de documento')
    num_doc = fields.Char(related='tip_doc.code')

    numero_documento = fields.Char(string='Número de documento')
    tax_id = fields.Many2one('account.tax', string='Impuesto')
    porcentaje_exoneracion = fields.Integer('Porcentaje de exoneración')
    cabys_ids = fields.Many2many('cabys', string='Cabys')
    fecha_emision = fields.Datetime('Fecha emisión')
    fecha_vencimiento = fields.Datetime('Fecha vencimiento')
    institucion = fields.Char(string='Institución')
    formato_fecha = fields.Char(string="Fecha de emisión de exoneracion", compute='_compute_tz_cr', default=" ")

    total_grabado = fields.Monetary('Total gravado', compute='_compute_exoneracion', default=0.0000)
    total_exonerado = fields.Monetary('Total exonerado', compute='_compute_exoneracion', default=0.0000)
    monto_exonerado = fields.Monetary('Monto exonerado', compute='_compute_exoneracion', default=0.0000)
    monto_grabado = fields.Monetary('Monto gravado', compute='_compute_exoneracion', default=0.0000)

    rpta_hacienda_string = fields.Text('Monto gravado')


    @api.depends('fecha_emision')
    def _compute_tz_cr(self):
        for tiempo in self:
            if tiempo.fecha_emision:
                tiempo.formato_fecha = (tiempo.fecha_emision).astimezone(pytz.timezone("America/Costa_Rica")).isoformat()
            else:
                tiempo.formato_fecha = ' '



    @api.depends('invoice_line_ids', 'amount_untaxed', 'amount_tax', 'check_exoneration', 'porcentaje_exoneracion')
    def _compute_exoneracion(self):
        for rec in self:
            if rec.check_exoneration == True:
                rec.total_grabado = rec.amount_untaxed * (1 - (rec.porcentaje_exoneracion / 100))
                rec.total_exonerado = rec.amount_untaxed * rec.porcentaje_exoneracion / 100
                if rec.amount_untaxed !=0:
                    ##actualizar en caso de utilizar productos y servicios
                    rec.monto_exonerado = ((rec.porcentaje_exoneracion / 100) / ((rec.total_exonerado + rec.amount_tax)/rec.amount_untaxed)) * rec.amount_untaxed
                    rec.monto_grabado = (1 - ((rec.porcentaje_exoneracion / 100) / ((rec.total_exonerado + rec.amount_tax)/rec.amount_untaxed))) * rec.amount_untaxed
                else:
                    rec.monto_exonerado = 0
                    rec.monto_grabado = 0

            else:
                rec.total_grabado = 0
                rec.total_exonerado = 0
                rec.monto_exonerado = 0
                rec.monto_grabado = 0


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id', 'total_exonerado', 'total_grabado')
    def _compute_amount(self):
        for move in self:

            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = move._get_lines_onchange_currency().currency_id

            for line in move.line_ids:
                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            if move.check_exoneration == True:
                move.amount_tax = (sign * (total_tax_currency if len(currencies) == 1 else total_tax)) - move.total_exonerado
                move.amount_total = (sign * (total_currency if len(currencies) == 1 else total)) - move.total_exonerado
                move.amount_residual = -sign * ((total_residual_currency if len(currencies) == 1 else total_residual) - move.total_exonerado)
                move.amount_total_signed = (abs(total) if move.move_type == 'entry' else -total - move.total_exonerado)
                move.amount_tax_signed = -total_tax - move.total_exonerado

            else:
                move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
                move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
                move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
                move.amount_tax_signed = -total_tax
            move.amount_untaxed_signed = -total_untaxed
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies or move.company_id.currency_id

            # Compute 'payment_state'.
            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

            if move.is_invoice(include_receipts=True) and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                    new_pmt_state = 'partial'

            if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

                # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                    new_pmt_state = 'reversed'

            move.payment_state = new_pmt_state

