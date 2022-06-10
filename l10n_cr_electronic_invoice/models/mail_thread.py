# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import dateutil
import email
import email.policy
import hashlib
import hmac
import lxml
import logging
import pytz
import re
import socket
import time
import threading

from collections import namedtuple
from email.message import EmailMessage
from email import message_from_string, policy
from lxml import etree
from werkzeug import urls
from xmlrpc import client as xmlrpclib

from odoo import _, api, exceptions, fields, models, tools, registry, SUPERUSER_ID
from odoo.exceptions import MissingError
from odoo.osv import expression

from odoo.tools import ustr
from odoo.tools.misc import clean_context, split_every

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):

        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        message = email.message_from_bytes(message, policy=email.policy.SMTP)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg_dict = self.message_parse(message, save_original=save_original)
        if strip_attachments:
            msg_dict.pop('attachments', None)

        result = self._eval_include_in_supplier_import(msg_dict)
        if result:
            pass
        else:
            return result

        existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg_dict['message_id'])], limit=1)
        if existing_msg_ids:
            _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                         msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return False

        # find possible routes for the message
        routes = self.message_route(message, msg_dict, model, thread_id, custom_values)
        thread_id = self._message_route_process(message, msg_dict, routes)
        return thread_id


    def _eval_include_in_supplier_import(self,msg_dict):
        fectchmail_server_id = self.env.context['default_fetchmail_server_id']
        if fectchmail_server_id:
            import_supplier = self.env['account.move.import.config'].sudo().search([('server_id','=',fectchmail_server_id)])
            if not import_supplier:
                _logger.info('No se encontro el fetchmail en ninguna configuración de importación.')
                return True #si no está en ninguna importación continúa
            elif import_supplier:
                if not 'attachments' in msg_dict:
                    _logger.info('Se encontró el fetchmail, pero no hay attachments para leer.')
                    return False #si no está en ninguna importación continúa
                elif 'attachments' in msg_dict and len(msg_dict['attachments'])==0:
                    _logger.info('Se encontró el fetchmail, pero los Se attachments para leer son cero')
                    return False
                elif 'attachments' in msg_dict and len(msg_dict['attachments'])>0:
                    _logger.info('Se encontró el fetchmail, si hay archivos para leer')
                    return True
            else:
                return True
        else:
            return True

