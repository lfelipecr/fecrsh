from odoo.exceptions import ValidationError, UserError
from odoo import _

def _validations_einvoice_pos(config):
    company_id = config.company_id
    if company_id.frm_ws_ambiente:
        if not config.sucursal:
            raise ValidationError(_('Para facturación electrónica debe tener configurada una sucursal.'))
        if not config.terminal:
            raise ValidationError(_('Para facturación electrónica debe tener configurada un terminal.'))
        if not config.sequence_fe_id:
            raise ValidationError(_('Para facturación electrónica debe tener configurada una secuencia para facturación dede POS.'))
        if not config.sequence_nc_id:
            raise ValidationError(_('Para facturación electrónica debe tener configurada un secuencia para nota de crédito dede POS.'))
        if not config.sequence_te_id:
            raise ValidationError(_('Para facturación electrónica debe tener configurada un secuencia para tiquete dede POS.'))
        if config.payment_method_ids:
            for pay in config.payment_method_ids:
                if not pay.payment_method_id:
                    raise ValidationError(_('Para el método de pago %s configure el método de pago electrónico' % (pay.name)))
                if not pay.account_payment_term_id:
                    raise ValidationError(_('Para el método de pago %s configure el término de pago electrónico' % (pay.name)))


        if not company_id.country_id:
            raise ValidationError(_('Asegúrese que la compañia tenga un país.'))
        if not company_id.state_id:
            raise ValidationError(_('Asegúrese que la compañia tenga un estado.'))
        if not company_id.county_id:
            raise ValidationError(_('Asegúrese que la compañia tenga un cantón.'))
        if not company_id.district_id:
            raise ValidationError(_('Asegúrese que la compañia tenga un distrito.'))
        if not company_id.neighborhood_id:
            raise ValidationError(_('Asegúrese que la compañia tenga un barrio.'))
        if not company_id.phone:
            raise ValidationError(_('Asegúrese que la compañia tenga un teléfono.'))
        if not company_id.email:
            raise ValidationError(_('Asegúrese que la compañia tenga un correo electrónico.'))

