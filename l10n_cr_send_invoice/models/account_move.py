import logging

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def action_invoice_sent(self):
        self.ensure_one()

        if not self.state_send_invoice and not self.state_tributacion:
            super(AccountInvoice, self).action_invoice_sent()
        else:
            self._send_mail_einvoice()

    def _send_mail(self):
        self._send_mail_einvoice()

    def _send_mail_einvoice(self):

        if self.tipo_documento == "FEC" or not (self.partner_id and self.partner_id.email):
            return

        if self.invoice_id.move_type == "in_invoice" or self.invoice_id.move_type == "in_refund":
            email_template = self.env.ref("l10n_cr_send_invoice.email_template_invoice_vendor")
        else:
            email_template = self.env.ref("account.email_template_edi_invoice")

        email_template.attachment_ids = [(5)]

        if self.partner_id and self.partner_id.email:
            email_values = {}

            # attachment_comprobante = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "account.move"), ("res_id", "=", self.id),
            #                                                                        ("res_field", "=", "xml_comprobante"), ], limit=1)
            # attachment_response = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "account.move"), ("res_id", "=", self.id),
            #                                                                     ("res_field", "=", "xml_respuesta_tributacion"), ], limit=1)

            attachment_search = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "account.move"),
                                                                               ("res_id", "=", self.id),
                                                                               ("res_field", "=", "xml_comprobante"),],limit=1)

            attachment_response = False
            attachment_comprobante = False

            if attachment_search:
                attachment_comprobante = self.env["ir.attachment"].browse(attachment_search[0]["id"])
                attachment_comprobante.name = self.fname_xml_comprobante

                attachment_resp_search = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "account.move"),
                                                                                       ("res_id", "=", self.id),
                                                                                       ("res_field", "=", "xml_respuesta_tributacion"),],limit=1)


                if attachment_resp_search:
                    attachment_response = self.env["ir.attachment"].browse(attachment_resp_search[0]["id"])
                    attachment_response.name = self.fname_xml_respuesta_tributacion

                if attachment_response and attachment_comprobante:
                    email_values['attachment_ids'] = [(4, attachment_comprobante[0]['id']), (4, attachment_response[0]['id'])]

            else:
                raise UserError(_("El comprobante debe tener xml"))

            # email_template.with_context(type="binary", default_type="binary").send_mail(self.id, raise_exception=False, force_send=True)
            email_template.sudo().send_mail(self.id, force_send=True, email_values=email_values, notif_layout='mail.mail_notification_light')
            self.write({"is_move_sent": True, "state_email": "sent"})

        else:
            raise UserError(_("Partner is not assigned to this invoice"))

    def update_state(self):
        super().update_state()
        if self.state_tributacion == 'aceptado' and self.move_type in ('out_invoice','out_refund','in_invoice'):
            self._send_mail()


