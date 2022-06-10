# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
import logging
_logger = logging.getLogger(__name__)


class AccountmoveGenerateXML(models.TransientModel):
    _name = 'account.move.generate.xml'
    _description = 'Generar nuevamente los xml (Facturación)'

    def _default_count(self):
        context = self.env.context
        if 'active_ids' in context:
            return len(self.env.context['active_ids'])
        else:
            return 1

    count = fields.Integer(default=_default_count)


    def process(self):
        context = self.env.context
        order_ids = ('active_ids' in context and context['active_ids']) or []

        invs_active = self.env['account.move'].sudo().browse(order_ids)
        if invs_active:
            for inv in invs_active:
                if inv.state_tributacion == 'aceptado':
                    if not inv.xml_comprobante:
                        inv._create_xml_comprobante()
                    if not inv.xml_respuesta_tributacion:
                        inv._reaload_response_xml()
