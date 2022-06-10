# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
import logging
_logger = logging.getLogger(__name__)


class OrderSendMail(models.TransientModel):
    _name = 'order.send.mail'
    _description = 'Enviar mail desde POS'

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

        orders_active = self.env['pos.order'].sudo().browse(order_ids)
        if orders_active:
            for order in orders_active:
                if order.state_tributacion == 'aceptado':
                    order._send_mail()
