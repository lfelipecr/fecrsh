# -*- coding: utf-8 -*-
import base64
import datetime
import logging
import requests
from threading import Lock
from xml.sax.saxutils import escape
from functools import partial

import pytz

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


lock = Lock()
_logger = logging.getLogger(__name__)

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    no_discount_amount = fields.Float(compute="_compute_discount_amount", store=True)
    discount_amount = fields.Float(compute="_compute_discount_amount", store=True)

    @api.depends("qty", "price_unit", "discount")
    def _compute_discount_amount(self):
        for record in self:
            record.no_discount_amount = record.qty * record.price_unit
            record.discount_amount = record.no_discount_amount * record.discount / 100
