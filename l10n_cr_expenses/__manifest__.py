# -*- coding: utf-8 -*-
{
    'name': "Expense - Invoice",
    'summary': """
        Gastos relacionados a facturas y pagos""",

    'description': """
        1. Generación de facturas mediante el módulo de gastos.
        2. Seleccione de factura por medio de informe de gastos.
        3. Pagos relacionados a facturas por medio del módulo de gastos.
    """,
    'author': "Jhonny Mack Merino Samillán",
    'company': 'BigCloud',
    'maintainer': 'Jhonny M. / Odoomatic',
    'website': "https://www.odoomatic.com",
    'category': 'Human Resources/Expenses',
    'version': '14.0.0.4',
    'depends': ["base", "hr_expense","account","l10n_cr_electronic_invoice"],
    'data': [
       'views/account_move_views.xml',
       'views/hr_expense_views.xml',

    ],
    'qweb': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
}
