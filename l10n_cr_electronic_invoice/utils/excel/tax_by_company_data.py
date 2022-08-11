from datetime import datetime, date
import calendar
amounts = [1,2,4,8,13]
classification_type = ['exempt','no_hold','exonerated']


CONDICION_IVA = {
    'acreditable': ['gecr','crpa','bica','prop'],
    'not_acreditable': ['gcnc',False],
    'all':  ['gecr','crpa','bica','prop','gcnc',False],
}

def _get_dates(mes):
    mes = int(mes)
    monthRange = calendar.monthrange(datetime.now().year, mes)
    i = date(datetime.now().year, mes, 1)
    f = date(datetime.now().year, mes, monthRange[1])
    return i, f



def _data(self):
    self_move = self.env['account.move'].sudo()
    if self.type_date == 'month':
        fecha_inicio, fecha_fin = _get_dates(self.selected_month)
    else:
        fecha_inicio, fecha_fin = self.selected_range_from, self.selected_range_to

    domain = [
        ('company_id', '=', self.company_id.id),
        ('journal_id', 'in', self.journal_ids.ids),
        #('activity_id','=',activity.id),
        #('activity_id','=',activity.id),
        ('state', '=', self.state_odoo),
        '|',('state_tributacion', '=', self.state_hacienda),('state_send_invoice','=',self.state_hacienda),
        ('invoice_date','>=', fecha_inicio), ('invoice_date','<=',fecha_fin),
    ]

    cols = {
        'vnt_na_bienes': {}, #ventas nacionales bienes
        'vnt_ex_bienes': {},  # ventas al exterior bienes
        'vnt_na_servicios': {}, #ventas nacionales servicios
        'vnt_ex_servicios': {}, #ventas al exterior servicios
        'com_na_bienes': {},  # ventas nacionales bienes
        'com_ex_bienes': {},  # ventas al exterior bienes
        'com_na_servicios': {},  # ventas nacionales servicios
        'com_ex_servicios': {},  # ventas al exterior servicios
    }

    #TODO: ******************************************************************** VENTAS ***********************************************
    sale_domain = domain + [('move_type', 'in', ('out_invoice','out_refund'))]

    #--------- VENTAS NACIONALES -------------
    vnt_na_bienes = False
    vnt_na_servicios = False
    if self.sale_national in ('national','all'):
        sale_domain_national = sale_domain + [('partner_id.country_id.code','=','CR')]
        sales_moves_nacional = self_move.search(sale_domain_national)
        if self.sale_type == 'other':  # Bien
            vnt_na_bienes = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.sale_type == 'service':
            vnt_na_servicios = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.sale_type == 'all':
            vnt_na_bienes = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            vnt_na_servicios = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass

    cols['vnt_na_bienes'] = sumatorias(self,vnt_na_bienes)
    cols['vnt_na_servicios'] = sumatorias(self,vnt_na_servicios)

    """
    #--------- out_invoice -------------
    vnt_na_bienes = False
    vnt_na_servicios = False
    if self.sale_national in ('national','all'):
        sale_domain_national = domain + [('move_type', '=', 'out_invoice'), ('partner_id.country_id.code','=','CR')]
        sales_moves_nacional = self_move.search(sale_domain_national)
        if self.sale_type == 'other':  # Bien
            vnt_na_bienes = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.sale_type == 'service':
            vnt_na_servicios = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.sale_type == 'all':
            vnt_na_bienes = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            vnt_na_servicios = sales_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass
    #--------- out_refund -------------
    vnt_na_bienes_re = False
    vnt_na_servicios_re = False
    if self.sale_national in ('national','all'):
        sale_domain_national_re = domain + [('move_type', '=', 'out_refund'),('partner_id.country_id.code','=','CR')]
        sales_moves_nacional_re = self_move.search(sale_domain_national_re)
        if self.sale_type == 'other':  # Bien
            vnt_na_bienes_re = sales_moves_nacional_re.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.sale_type == 'service':
            vnt_na_servicios_re = sales_moves_nacional_re.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.sale_type == 'all':
            vnt_na_bienes_re = sales_moves_nacional_re.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            vnt_na_servicios_re = sales_moves_nacional_re.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass

    cols['vnt_na_bienes'] = sumatorias(vnt_na_bienes) - sumatorias(vnt_na_bienes_re)
    cols['vnt_na_servicios'] = sumatorias(vnt_na_servicios) - sumatorias(vnt_na_servicios_re)

    """

    # --------- VENTAS INTERNACIONALES -------------

    vnt_ex_bienes = False
    vnt_ex_servicios = False
    if self.sale_national in ('international','all'):
        sale_domain_inter = sale_domain + [('partner_id.country_id.code', '!=', 'CR')]
        sales_moves_internacional = self_move.search(sale_domain_inter)
        if self.sale_type == 'other':  # Bien
            vnt_ex_bienes = sales_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.sale_type == 'service':
            vnt_ex_servicios = sales_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.sale_type == 'all':
            vnt_ex_bienes = sales_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            vnt_ex_servicios = sales_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass

    cols['vnt_ex_bienes'] = sumatorias(self,vnt_ex_bienes)
    cols['vnt_ex_servicios'] = sumatorias(self,vnt_ex_servicios)


    #TODO: ******************************************************************** COMPRAS ***********************************************


    purchase_domain = domain + [('move_type', 'in', ('in_invoice','in_refund'))]

    # --------- COMPRAS NACIONALES -------------

    com_na_bienes = False
    com_na_servicios = False
    if self.purchase_national in ('national', 'all'):
        purchase_domain_national = purchase_domain + [('partner_id.country_id.code', '=', 'CR')]
        purchase_moves_nacional = self_move.search(purchase_domain_national)
        if self.purchase_type == 'other':  # Bien
            com_na_bienes = purchase_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.purchase_type == 'service':
            com_na_servicios = purchase_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.purchase_type == 'all':
            com_na_bienes = purchase_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            com_na_servicios = purchase_moves_nacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass

    cols['com_na_bienes'] = sumatorias(self,com_na_bienes)
    cols['com_na_servicios'] = sumatorias(self,com_na_servicios)

    # --------- COMPRAS INTERNACIONALES -------------

    com_ex_bienes = False
    com_ex_servicios = False
    if self.purchase_national in ('international', 'all'):
        purchase_domain_inter = purchase_domain + [('partner_id.country_id.code', '!=', 'CR')]
        purchase_moves_internacional = self_move.search(purchase_domain_inter)
        if self.purchase_type == 'other':  # Bien
            com_ex_bienes = purchase_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
        elif self.purchase_type == 'service':
            com_ex_servicios = purchase_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        elif self.purchase_type == 'all':
            com_ex_bienes = purchase_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type != 'service')
            com_ex_servicios = purchase_moves_internacional.invoice_line_ids.filtered(lambda sb: sb.product_id.type == 'service')
        else:
            pass

    cols['com_ex_bienes'] = sumatorias(self,com_ex_bienes)
    cols['com_ex_servicios'] = sumatorias(self,com_ex_servicios)

    return cols



def sumatorias(self,move_lines):
    r_amounts = {
        'amount_1': 0.0,
        'amount_2': 0.0,
        'amount_4': 0.0,
        'amount_8': 0.0,
        'amount_13': 0.0,
        'amount_exempt': 0.0,
        'amount_no_hold': 0.0,
        'amount_exonerated': 0.0,
        'total': 0.0,
    }

    move_ids = []
    if move_lines:
        for li in move_lines:
            move_ids.append(li.move_id.id)
        invoices = self.env['account.move'].search([('id','in',list(set(move_ids)))])
        for inv in invoices:    
            for line in inv.line_ids:
                if line.tax_line_id:
                    for tax in line.tax_line_id:
                        if tax.classification_type == 'none':
                            for amount in amounts:
                                if amount == tax.amount:
                                    if not inv.check_exoneration:
                                        r_amounts['amount_' + str(amount)] += abs(line.amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(line.amount_currency)*-1
                                    else:
                                        if inv.tax_id == line.tax_line_id:
                                            price_subtotal = line.tax_base_amount
                                            amount_currency = abs(line.amount_currency)
                                            amount_exoneration = (inv.porcentaje_exoneracion*price_subtotal/100)
                                            amount_currency = amount_currency-amount_exoneration
                                            r_amounts['amount_exonerated'] += amount_exoneration
                                            r_amounts['amount_' + str(amount)] += abs(amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(amount_currency)*-1
                                        else:
                                            r_amounts['amount_' + str(amount)] += abs(line.amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(line.amount_currency)*-1
                                                 
                        elif tax.classification_type in classification_type:
                            for cla in classification_type:
                                if cla == tax.classification_type:
                                    if not inv.check_exoneration:
                                        r_amounts['amount_' + str(cla)] += abs(line.amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(line.amount_currency)*-1
                                    else:
                                        if line.tax_id == line.tax_line_id:
                                            price_subtotal = line.tax_base_amount
                                            amount_currency = abs(line.amount_currency)
                                            amount_exoneration = (inv.porcentaje_exoneracion*price_subtotal/100)
                                            amount_currency = amount_currency-amount_exoneration
                                            r_amounts['amount_exonerated'] += amount_exoneration
                                            r_amounts['amount_' + str(amount)] += abs(amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(amount_currency)*-1
                                        else:
                                            r_amounts['amount_' + str(amount)] += abs(line.amount_currency) if line.move_id.move_type in ('in_invoice','out_invoice') else abs(line.amount_currency)*-1
                                    

    r_amounts['total'] = r_amounts['amount_1'] + r_amounts['amount_2'] + r_amounts['amount_4'] + r_amounts['amount_8'] + r_amounts['amount_13']+ \
                         r_amounts['amount_exempt'] + r_amounts['amount_no_hold'] + r_amounts['amount_exonerated']

    return r_amounts

