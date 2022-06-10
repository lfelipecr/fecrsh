# -*- coding: utf-8 -*-
{
    'name': "POS Electrónico",
    'summary': """
        Punto de Venta - Electrónico""",

    'description': """
        Envío a Hacienda de compobantes electrónicos mediante POS.
    """,
    'author': "Jhonny Mack Merino Samillán",
    'company': 'BigCloud',
    'maintainer': 'Jhonny M. / BigCloud',
    'website': "https://www.bigcloud.com",
    'category': 'POS / Envío-electrónico',
    'version': '14.0.5.2',
    'depends': ['point_of_sale', 'account', 'l10n_cr_electronic_invoice'],
    'data': [
        'security/ir.model.access.csv',

        'reports/pos_order_report.xml',
        'data/cron.xml',
        'data/pos_config.xml',
        'data/pos_mail_template.xml',
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        #'views/pos_report.xml',
        'views/pos_payment_method_views.xml',

        #************ Assets *********+
        'views/assets.xml',

        #************ Wizards *********+
        'wizard/pos_order_generate_wizard.xml',
        'wizard/pos_order_mail_wizard.xml',

    ],
    'qweb': ['static/src/xml/OrderReceipt.xml',
             'static/src/xml/ClientDetailsEdit.xml',
             'static/src/xml/PaymentScreen.xml',
             'static/src/xml/ProductDiscountService.xml',
             ],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
}
