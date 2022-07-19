from odoo import fields, models, api


class InvoiceLineElectronic(models.Model):
    _inherit = "account.move.line"

    tariff_head = fields.Char(
        string="Tariff heading for export invoice",
        required=False,
    )

    def _onchange_balance(self):
        for line in self:
            if line.currency_id:
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
        index=True, compute="_compute_analytic_account_id", check_company=True, copy=True, related='move_id.ac_analytic_id')
    info_json = fields.Text('Información')


    @api.depends('move_id', 'product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                #if rec:
                    #record.analytic_account_id = rec.analytic_id

            
           # record.analytic_account_id = record.move_id.ac_analytic_id


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ac_move_ref = fields.Many2one('account.move', string='Journal Item', ondelete='cascade', index=True, check_company=True)