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
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_cr_electronic_invoice import cr_edi


NIF_API = "https://api.hacienda.go.cr/fe/ae"
lock = Lock()
_logger = logging.getLogger(__name__)

TRIBUTATION_STATE= [
            ("aceptado", "Aceptado"),
            ("rechazado", "Rechazado"),
            ("rejected", "Rechazado2"),
            ("no_encontrado", "No encontrado"),
            ("recibido", "Recibido"),
            ("firma_invalida", "Firma Inválida"),
            ("error", "Error"),
            ("procesando", "Procesando"),
        ]

class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = "pos.order", "mail.thread"

    is_return = fields.Boolean(string='Retorno')
    envio_hacienda = fields.Boolean(string='Envio a Hacienda')

    invoice_amount_text = fields.Char(
        compute="_compute_invoice_amount_text",
    )
    total_services_taxed = fields.Float(
        compute="_compute_total_amounts",
    )
    total_services_exempt = fields.Float(
        compute="_compute_total_amounts",
    )
    total_products_taxed = fields.Float(
        compute="_compute_total_amounts",
    )
    total_products_exempt = fields.Float(
        compute="_compute_total_amounts",
    )
    total_taxed = fields.Float(
        compute="_compute_total_taxed",
    )
    total_exempt = fields.Float(
        compute="_compute_total_exempt",
    )
    total_sale = fields.Float(
        compute="_compute_total_sale",
    )
    total_discount = fields.Float(
        compute="_compute_total_discount",
    )
    total_others = fields.Float(
        compute="_compute_total_others",
    )

    @api.depends("amount_total")
    def _compute_invoice_amount_text(self):
        for record in self:
            record.invoice_amount_text = record.currency_id.amount_to_text(record.amount_total)

    @api.depends("lines")
    def _compute_total_amounts(self):
        for record in self:
            record.total_services_taxed = sum(record.lines.filtered(lambda l: l.product_id.type == "service" and l.tax_ids).mapped("price_subtotal"))
            record.total_services_exempt = sum(record.lines.filtered(lambda l: l.product_id.type == "service" and not l.tax_ids).mapped("price_subtotal"))
            record.total_products_taxed = sum(record.lines.filtered(lambda l: l.product_id.type != "service" and l.tax_ids).mapped("price_subtotal"))
            record.total_products_exempt = sum(record.lines.filtered(lambda l: l.product_id.type != "service" and not l.tax_ids).mapped("price_subtotal"))

    @api.depends("total_products_taxed", "total_services_taxed")
    def _compute_total_taxed(self):
        for record in self:
            record.total_taxed = record.total_products_taxed + record.total_services_taxed

    @api.depends("total_products_exempt", "total_services_exempt")
    def _compute_total_exempt(self):
        for record in self:
            record.total_exempt = record.total_products_exempt + record.total_services_exempt

    @api.depends("total_products_taxed", "total_services_taxed")
    def _compute_total_sale(self):
        for record in self:
            record.total_sale = record.total_taxed + record.total_exempt

    def _compute_total_discount(self):
        for record in self:
            record.total_discount = sum(record.lines.mapped("discount_amount"))

    def _compute_total_others(self):
        for record in self:
            record.total_others = 0  # TODO

    @api.model
    def sequence_number_sync(self, vals):
        tipo_documento = vals.get("tipo_documento", False)
        sequence = vals.get("sequence", False)
        sequence = int(sequence) if sequence else False
        if vals.get("session_id") and sequence:
            session = self.env["pos.session"].sudo().browse(vals["session_id"])
            if (tipo_documento == "FE"and sequence >= session.config_id.sequence_fe_id.number_next_actual):
                session.config_id.sequence_fe_id.number_next_actual = sequence + 1
            elif (tipo_documento == "TE"and sequence >= session.config_id.sequence_te_id.number_next_actual):
                session.config_id.sequence_te_id.number_next_actual = sequence + 1

    def _get_type_documento(self,ui_order,vals):
        if 'is_return' in vals:
            if vals['is_return']:
                type_document = 'NC'
            elif not ui_order.get('partner_id'):
                type_document = 'TE'
            else:
                type_document = 'FE'
        else:
            if not ui_order.get('partner_id'):
                type_document = 'TE'
            else:
                type_document = 'FE'

        return type_document


    @api.model
    def _order_fields(self, ui_order):
        vals = super(PosOrder, self)._order_fields(ui_order)
        session = self.env['pos.session'].sudo().browse(vals.get('session_id'))
        vals['envio_hacienda'] = ui_order.get('envio_hacienda')

        _logger.info("POS - Enviar a hacienda ? %s " % (vals['envio_hacienda']))

        if ui_order.get('envio_hacienda') or not session.config_id.show_send_hacienda and session:
            vals['envio_hacienda'] = True
            vals["tipo_documento"] = self._get_type_documento(ui_order,vals)
            vals["sequence"] = ui_order.get("sequence")
            vals["number_electronic"] = ui_order.get("number_electronic")
            # TODO: EL CAMPO POR_ORDER_ID CUMPLE LA MISMA FUNCIÓN, PERO NOPERTENECE A ESTE MÓDULO
            if 'return_order_ref' in ui_order:
                if ui_order.get('return_order_ref') != False:
                    vals['pos_order_id'] = int(ui_order['return_order_ref'])

            _logger.info("POS - Tipo de documento %s " % (vals['tipo_documento']))
        else:
            vals['envio_hacienda'] = False
        return vals

    @api.model
    def create(self, vals):
        session = self.env['pos.session'].sudo().browse(vals['session_id'])
        vals = self._complete_values_from_session(session, vals)
        if vals["envio_hacienda"] or not session.config_id.show_send_hacienda and session:
            vals['envio_hacienda'] = True
            if vals["tipo_documento"] == 'FE':
                seq = session.config_id.sequence_fe_id.next_by_id()
            elif vals["tipo_documento"] == 'TE':
                seq = session.config_id.sequence_te_id.next_by_id()
            elif vals["tipo_documento"] == 'NC':
                seq = session.config_id.sequence_te_id.next_by_id()
            else:
                raise UserError(_("No se generó el tipo de documento"))

            sequence = cr_edi.utils.compute_full_sequence(
                session.config_id.sucursal,
                session.config_id.terminal,
                vals["tipo_documento"],
                seq
            )
            vals["sequence"] = sequence
            number = cr_edi.utils.get_number_electronic(self.env.company, sequence)
            vals["number_electronic"] = number
            _logger.info('Secuencia en POS: %s' % (sequence))
            _logger.info('Número electrónico en POS: %s' % (number))
        else:
            vals['envio_hacienda'] = False
        return super().create(vals)
        #return order

    number_electronic = fields.Char(string="Número electrónico",required=False,copy=False,index=True,tracking=True)
    date_issuance = fields.Char(string="Fecha de emisión",required=False,copy=False,)
    tipo_documento = fields.Selection(selection=[
        ("FE", "Factura Electrónica Normal"),
        ("TE", "Tiquete Electrónico"),
        ("NC", "Nota de Crédito"),
    ], string="Tipo Comprobante", required=False, default="FE")
    state_tributacion = fields.Selection(TRIBUTATION_STATE,string="Estado actual",copy=False,tracking=True)
    reference_code_id = fields.Many2one(comodel_name="reference.code",string="Código de referencia",required=False,)
    pos_order_id = fields.Many2one(comodel_name="pos.order",string="Documento de referencia",required=False,copy=False,)

    #XML ENVIO
    xml_respuesta_tributacion = fields.Binary(string="Rpta.Hacienda XML",required=False,copy=False,attachment=True,tracking=True)
    fname_xml_respuesta_tributacion = fields.Char(string="Nombre de archivo XML Respuesta Tributación",required=False,copy=False,)

    #XML RESPUESTA
    xml_comprobante = fields.Binary(string="Comprobante XML",required=False,copy=False,attachment=True,tracking=True)
    fname_xml_comprobante = fields.Char(string="Nombre de archivo Comprobante XML",required=False,copy=False,)
    state_email = fields.Selection(
        selection=[
            ("no_email", "Sin cuenta de correo"),
            ("sent", "Enviado"),
            ("fe_error", "Error FE"),
        ],string="Estado email",copy=False,tracking=True)
    error_count = fields.Integer(string="Cantidad de errores",required=False,default="0",)

    sequence = fields.Char(
        string="Consecutivo",
        readonly=True,tracking=True
    )
    _sql_constraints = [
        (
            "number_electronic_uniq",
            "unique (number_electronic)",
            "La clave de comprobante debe ser única",
        ),
    ]

    def action_pos_order_paid(self):
        for order in self:
            if order.pos_order_id:
                order.name = order.session_id.config_id.sequence_nc_id._next()
        return super(PosOrder, self).action_pos_order_paid()

    def refund(self):
        po = self.env["pos.order"]
        reference_code_id = self.env["reference.code"].search([("code", "=", "01")], limit=1)
        current_session = self.env["pos.session"].search(
            [
                ("state", "!=", "closed"),
                ("user_id", "=", self.env.uid),
                ("name", "not like", "RESCUE"),
            ],
            limit=1,
        )
        if not current_session:
            raise UserError(
                _(
                    "To return product(s), you need to open a session that will be used to register the refund."
                )
            )
        for order in self:
            clone = order.copy(
                {
                    "name": order.name + _(" REFUND"),
                    "session_id": current_session.id,
                    "date_order": fields.Datetime.now(),
                    "pos_order_id": order.id,
                    "reference_code_id": reference_code_id.id,
                }
            )
            po += clone
        for clone in po:
            for order_line in clone.lines:
                order_line.write({"qty": -order_line.qty})
        return {
            "name": _("Return Products"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "pos.order",
            "res_id": po.ids[0],
            "view_id": False,
            "context": self.env.context,
            "type": "ir.actions.act_window",
            "target": "current",
        }

    @api.model
    def _consultahacienda_pos(self, max_orders=1):
        pos_orders = self.env["pos.order"].search(
            [
                ("state", "in", ("paid", "done", "invoiced")),
                ("number_electronic", "!=", False),
                ("state_tributacion", "in", ("recibido", "procesando")),
            ],
            limit=max_orders,
        )
        total_orders = len(pos_orders)
        current_order = 0
        _logger.info("MAB - Consulta Hacienda - POS Orders to check: %s", total_orders)
        for doc in pos_orders:
            current_order += 1
            _logger.info(
                "MAB - Consulta Hacienda - POS Order %s / %s",
                current_order,
                total_orders,
            )
            token_m_h = cr_edi.auth.get_token(
                internal_id=doc.company_id.id,
                username=doc.company_id.frm_ws_identificador,
                password=doc.company_id.frm_ws_password,
                client_id=doc.company_id.frm_ws_ambiente,
            )
            if doc.number_electronic and len(doc.number_electronic) == 50:
                response_json = cr_edi.api.query_document(
                    clave=doc.number_electronic,
                    token=token_m_h,
                    client_id=doc.company_id.frm_ws_ambiente,
                )
                status = response_json["status"]
                if status == 200:
                    estado_m_h = response_json.get("ind-estado")
                elif status == 400:
                    estado_m_h = response_json.get("ind-estado")
                    _logger.error(
                        "MAB - Error: %s Documento:%s no encontrado en Hacienda",
                        estado_m_h,
                        doc.number_electronic,
                    )
                else:
                    _logger.error("MAB - Error inesperado en Consulta Hacienda - Abortando")
                    return
                if estado_m_h == "aceptado":
                    doc.state_tributacion = estado_m_h
                    doc.fname_xml_respuesta_tributacion = "AHC_" + doc.number_electronic + ".xml"
                    doc.xml_respuesta_tributacion = response_json.get("respuesta-xml")
                    if doc.partner_id and doc.partner_id.email:
                        doc._send_mail()
                    else:
                        doc.state_email = "no_email"
                        _logger.info("email no enviado - cliente no definido")
                elif estado_m_h == "firma_invalida":
                    if doc.error_count > 10:
                        doc.state_tributacion = estado_m_h
                        doc.fname_xml_respuesta_tributacion = (
                            "AHC_" + doc.number_electronic + ".xml"
                        )
                        doc.xml_respuesta_tributacion = response_json.get("respuesta-xml")
                        doc.state_email = "fe_error"
                        _logger.info("email no enviado - factura rechazada")
                    else:
                        doc.error_count += 1
                        doc.state_tributacion = "procesando"
                elif estado_m_h in ("rechazado", "rejected"):
                    doc.state_tributacion = estado_m_h
                    doc.fname_xml_respuesta_tributacion = "AHC_" + doc.number_electronic + ".xml"
                    doc.xml_respuesta_tributacion = response_json.get("respuesta-xml")
                    doc.state_email = "fe_error"
                    _logger.info("email no enviado - factura rechazada")
                elif estado_m_h == "error":
                    doc.state_tributacion = estado_m_h
                    doc.state_email = "fe_error"
                else:
                    if doc.error_count > 10:
                        doc.state_tributacion = "error"
                    elif doc.error_count < 4:
                        doc.error_count += 1
                        doc.state_tributacion = "procesando"
                    else:
                        doc.error_count += 1
                        doc.state_tributacion = ""
                    _logger.error(
                        "MAB - Consulta Hacienda - POS Order not found: %s",
                        doc.number_electronic,
                    )
            else:
                doc.state_tributacion = "error"
                _logger.error(
                    "MAB - POS Order %s  - x Number Electronic: %s formato incorrecto",
                    doc.name,
                    doc.number_electronic,
                )
        _logger.info("MAB - Consulta Hacienda POS- Finalizad Exitosamente")


    @api.model
    def search_order(self, uid):
        pos_order = self.env['pos.order'].search([('pos_reference','like',uid)])
        if pos_order:
            value = {
                "number_electronic": pos_order.number_electronic,
                "sequence": pos_order.sequence,
                "tipo_documento": pos_order.tipo_documento,
            }
            return json.dumps(value)
        else:
            return False

    def get_amounts(self):
        self.ensure_one()
        amounts = {
            "service_taxed": 0,
            "service_no_taxed": 0,
            "service_exempt": 0,  # TODO
            "product_taxed": 0,
            "product_no_taxed": 0,
            "product_exempt": 0,  # TODO
            "discount": 0,
            "other_charges": 0,  # TODO
        }
        for line in self.lines:

            no_discount_amount = line.qty * line.price_unit
            discount_amount = round((line.qty * line.price_unit) * (line.discount/100),2)
            amounts["discount"] += discount_amount
            line_type = "service" if line.product_id.type == "service" else "product"
            is_tax = "taxed" if line.tax_ids_after_fiscal_position else "no_taxed"
            amounts[line_type + "_" + is_tax] += no_discount_amount # TODO Exempt
        return amounts


    @api.model
    def _validahacienda_pos(self, max_orders=1, no_partner=True):
        self.send_hacienda(max_orders, no_partner)


    def send_hacienda(self,max_orders, no_partner):
        pos_orders = self.env["pos.order"].search([
            ("state", "in", ("paid", "done", "invoiced")), "|", (no_partner, "=", True),
            ("partner_id", "!=", False), ("state_tributacion", "=", False),('envio_hacienda','=',True)  ],
            order="date_order desc",
            limit=max_orders,
        )
        total_orders = len(pos_orders)
        current_order = 0
        _logger.info("MAB - Valida Hacienda - POS Orders to check: %s", total_orders)
        for doc in pos_orders:
            current_order += 1
            _logger.info("MAB - Valida Hacienda - POS Order %s / %s", current_order, total_orders)
            docName = doc.number_electronic
            if not docName:
                continue
            if not docName.isdigit() or doc.company_id.frm_ws_ambiente == "disabled":
                _logger.warning("MAB - Valida Hacienda - Omitir factura %s", docName)
                continue

            if doc.is_return == True and doc.amount_total > 0:
                _logger.error(
                    "MAB - Error documento %s tiene monto positivo, pero es nota de crédito en POS. ",
                    doc.number_electronic,
                )
                continue
            if doc.is_return == False and doc.amount_total < 0:
                _logger.error(
                    "MAB - Error documento %s tiene monto negativo, cuando no es nota de crédito POS. ",
                    doc.number_electronic,
                )
                continue

            if not doc.xml_comprobante:
                doc, date_cr = self.reload_xml(doc)

            token_m_h = cr_edi.auth.get_token(
                internal_id=doc.company_id.id,
                username=doc.company_id.frm_ws_identificador,
                password=doc.company_id.frm_ws_password,
                client_id=doc.company_id.frm_ws_ambiente,
            )
            # response_json = cr_edi.api.send_xml(
            #     doc.company_id.frm_ws_ambiente,
            #     token_m_h,
            #     doc.xml_comprobante,
            #     date_cr,
            #     doc.electronic_number,
            #     doc.company_id,
            #     doc.partner_id,
            # )
            response_json = cr_edi.api.send_xml(
                client_id=doc.company_id.frm_ws_ambiente,
                token=token_m_h,
                xml=base64.b64decode(doc.xml_comprobante),
                date=date_cr,
                electronic_number=doc.number_electronic,
                issuer=doc.company_id,
                receiver=doc.partner_id,
            )
            response_status = response_json.get("status")
            response_text = response_json.get("text")
            if 200 <= response_status <= 299:
                doc.state_tributacion = "procesando"
            else:
                if response_text.find("ya fue recibido anteriormente") != -1:
                    doc.state_tributacion = "procesando"
                    # doc.message_post(
                    #     subject=_("Error"),
                    #     body=_("Ya recibido anteriormente, se pasa a consultar"),
                    # )
                elif doc.error_count > 10:
                    # doc.message_post(subject=_("Error"), body=response_text)
                    doc.state_tributacion = "error"
                    _logger.error(
                        "MAB - Invoice: %s  Status: %s Error sending XML: %s",
                        doc.name,
                        response_status,
                        response_text,
                    )
                else:
                    doc.error_count += 1
                    doc.state_tributacion = "procesando"
                    # doc.message_post(subject=_("Error"), body=response_text)
                    _logger.error(
                        "MAB - Invoice: %s  Status: %s Error sending XML: %s",
                        doc.name,
                        response_status,
                        response_text,
                    )
        _logger.info("MAB 014 - Valida Hacienda POS- Finalizado Exitosamente")

    #METODO COPIADO DE l10n_cr_vat_validation PARA TRAER DATOS DEL CLIENTE
    @api.model
    def _get_name_from_vat(self,vat):
        if not self.vat:
            return
        response = requests.get(NIF_API, params={"identificacion": vat})
        if response.status_code == 200:
            response_json = response.json()
            return response_json
        elif response.status_code == 404:
            title = "VAT Not found"
            message = "The VAT is not on the API"
        elif response.status_code == 400:
            title = "API Error 400"
            message = "Bad Request"
        else:
            title = "Unknown Error"
            message = "Unknown error in the API request"
        return {
            "warning": {
                "title": title,
                "message": message,
            }
        }

    @api.model
    def _process_order(self, order, draft, existing_order):
        if existing_order and existing_order.display_name == '/' and 'envio_hacienda' in order['data']:
            if order['data']['envio_hacienda']:
                o = self.env['pos.order'].sudo().browse(existing_order.id)
                o.sudo().lines.unlink()
                o.sudo().unlink()
                existing_order = False
        return super(PosOrder, self)._process_order(order, draft, existing_order)


    #Nuevo 03-02-21

    def reload_xml(self, document=False):
        if not document:
            document = self
        for doc in document:
            docName = doc.number_electronic

            now_utc = datetime.datetime.now(pytz.timezone("UTC"))
            now_cr = now_utc.astimezone(pytz.timezone("America/Costa_Rica"))
            dia = docName[3:5]
            mes = docName[5:7]
            anno = docName[7:9]
            date_cr = now_cr.strftime("20" + anno + "-" + mes + "-" + dia + "T%H:%M:%S-06:00")
            codigo_seguridad = docName[-8:]
            if not doc.payment_ids.payment_method_id.payment_method_id.ids:
                _logger.warning(
                    "MAB 001 - codigo seguridad : %s  -- Pedido: %s Metodo de pago de diario no definido, utilizando efectivo",
                    codigo_seguridad,
                    docName,
                )
            # sale_conditions = "01"
            currency_rate = 1
            lines = dict()
            otros_cargos = dict()
            otros_cargos_id = 0
            line_number = 0
            total_servicio_gravado = 0.0
            total_servicio_exento = 0.0
            # total_servicio_exonerado = 0.0  # TODO use
            total_mercaderia_gravado = 0.0
            total_mercaderia_exento = 0.0
            # total_mercaderia_exonerado = 0.0  # TODO use
            total_descuento = 0.0
            total_impuestos = 0.0
            base_subtotal = 0.0
            total_otros_cargos = 0.0
            for line in doc.lines:
                line_number += 1
                price = line.price_unit * (1 - line.discount / 100.0)
                qty = abs(line.qty)
                if not qty:
                    continue
                fpos = line.order_id.fiscal_position_id
                tax_ids = (
                    fpos.map_tax(line.tax_ids, line.product_id, line.order_id.partner_id)
                    if fpos
                    else line.tax_ids
                )
                line_taxes = tax_ids.compute_all(
                    price,
                    line.order_id.pricelist_id.currency_id,
                    1,
                    product=line.product_id,
                    partner=line.order_id.partner_id,
                )
                # ajustar para IVI
                price_unit = round(
                    line_taxes["total_excluded"] / (1 - line.discount / 100.0), 5
                )
                base_line = abs(round(price_unit * qty, 5))
                subtotal_line = abs(round(price_unit * qty * (1 - line.discount / 100.0), 5))
                dline = {
                    "cantidad": qty,
                    "unidadMedida": line.product_id and line.product_id.uom_id.code or "Sp",
                    "cabys_code": line.product_id.cabys_id.code,
                    "detalle": escape(line.product_id.name[:159]),
                    "precioUnitario": price_unit,
                    "montoTotal": base_line,
                    "subtotal": subtotal_line,
                }
                if line.discount:
                    descuento = abs(round(base_line - subtotal_line, 5))
                    total_descuento += descuento
                    dline["montoDescuento"] = descuento
                    dline["naturalezaDescuento"] = "Descuento Comercial"
                taxes = dict()
                _line_tax = 0.0
                if tax_ids:
                    tax_index = 0
                    taxes_lookup = {}
                    for i in tax_ids:
                        taxes_lookup[i.id] = {
                            "tax_code": i.tax_code,
                            "tarifa": i.amount,
                            "iva_tax_desc": i.iva_tax_desc,
                            "iva_tax_code": i.iva_tax_code,
                        }
                    tax_amount = 0
                    for i in line_taxes["taxes"]:
                        if taxes_lookup[i["id"]]["tax_code"] == "service":
                            total_otros_cargos += tax_amount
                        elif taxes_lookup[i["id"]]["tax_code"] != "00":
                            tax_index += 1
                            tax_amount = abs(round(i["amount"], 5) * qty)
                            _line_tax += tax_amount
                            taxes[tax_index] = {
                                "codigo": taxes_lookup[i["id"]]["tax_code"],
                                "tarifa": taxes_lookup[i["id"]]["tarifa"],
                                "monto": tax_amount,
                                "iva_tax_desc": taxes_lookup[i["id"]]["iva_tax_desc"],
                                "iva_tax_code": taxes_lookup[i["id"]]["iva_tax_code"],
                            }
                dline["impuesto"] = taxes
                dline["impuestoNeto"] = _line_tax
                if line.product_id and line.product_id.type == "service":
                    if taxes:
                        total_servicio_gravado += base_line
                        total_impuestos += _line_tax
                    else:
                        total_servicio_exento += base_line
                else:
                    if taxes:
                        total_mercaderia_gravado += base_line
                        total_impuestos += _line_tax
                    else:
                        total_mercaderia_exento += base_line
                base_subtotal += subtotal_line
                dline["montoTotalLinea"] = subtotal_line + _line_tax
                lines[line_number] = dline
            if total_otros_cargos:
                otros_cargos_id = 1
                tax_amount = abs(round(i["amount"], 5) * qty)
                otros_cargos[otros_cargos_id] = {
                    "TipoDocumento": taxes_lookup[i["id"]]["iva_tax_code"],
                    "Detalle": escape(taxes_lookup[i["id"]]["iva_tax_desc"]),
                    "MontoCargo": total_otros_cargos,
                }
            doc.date_issuance = date_cr
            # invoice_comments = ""
            xml_string_builder = cr_edi.gen_xml.gen(doc)
            # xml_to_sign = str(xml_string_builder)
            xml_firmado = cr_edi.utils.sign_xml(
                cert=doc.company_id.signature,
                pin=doc.company_id.frm_pin,
                xml=xml_string_builder,
            )
            doc.fname_xml_comprobante = doc.tipo_documento + "_" + docName + ".xml"
            doc.xml_comprobante = base64.encodebytes(xml_firmado)
            _logger.info("MAB - SIGNED XML:%s", doc.fname_xml_comprobante)

            return doc, date_cr


    def reload_response_xml(self):
        doc = self
        token_m_h = cr_edi.auth.get_token(
            internal_id=doc.company_id.id,
            username=doc.company_id.frm_ws_identificador,
            password=doc.company_id.frm_ws_password,
            client_id=doc.company_id.frm_ws_ambiente,
        )
        if doc.number_electronic and len(doc.number_electronic) == 50:
            response_json = cr_edi.api.query_document(
                clave=doc.number_electronic,
                token=token_m_h,
                client_id=doc.company_id.frm_ws_ambiente,
            )
            status = response_json["status"]
            if status == 200:
                estado_m_h = response_json.get("ind-estado")
            elif status == 400:
                estado_m_h = response_json.get("ind-estado")
                _logger.error(
                    "MAB - Error: %s Documento:%s no encontrado en Hacienda",
                    estado_m_h,
                    doc.number_electronic,
                )
            else:
                _logger.error("MAB - Error inesperado en Consulta Hacienda - Abortando")
                return
            if estado_m_h == "aceptado":
                doc.state_tributacion = estado_m_h
                doc.fname_xml_respuesta_tributacion = "AHC_" + doc.number_electronic + ".xml"
                doc.xml_respuesta_tributacion = response_json.get("respuesta-xml")



    def _send_mail(self):
        if not self.xml_comprobante or not self.xml_respuesta_tributacion:
            raise ValidationError(_("Asegúrese de tener los xml de envío y respuesta de hacienda."))

        if self.partner_id and self.partner_id.email:
            email_values = {}
            email_template = self.env.ref("l10n_cr_pos.email_template_pos_invoice", False)
            attachment_search = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "pos.order"),
                                                                              ("res_id", "=", self.id),
                                                                              ("res_field", "=", "xml_comprobante"), ], limit=1)
            attachment_response = False
            attachment_comprobante = False
            if attachment_search:
                attachment_comprobante = self.env["ir.attachment"].browse(attachment_search[0]["id"])
                attachment_comprobante.name = self.fname_xml_comprobante

                attachment_resp_search = self.env["ir.attachment"].sudo().search_read([("res_model", "=", "pos.order"),
                                                                                       ("res_id", "=", self.id),
                                                                                       ("res_field", "=", "xml_respuesta_tributacion"), ], limit=1)

                if attachment_resp_search:
                    attachment_response = self.env["ir.attachment"].browse(attachment_resp_search[0]["id"])
                    attachment_response.name = self.fname_xml_respuesta_tributacion

                if attachment_response and attachment_comprobante:
                    email_values['attachment_ids'] = [(4, attachment_comprobante[0]['id']), (4, attachment_response[0]['id'])]


            else:
                raise UserError(_("El comprobante debe tener xml"))

            email_template.sudo().send_mail(self.id, force_send=True, email_values=email_values, notif_layout='mail.mail_notification_light')
            self.state_email = "sent"

