# -*- coding: utf-8 -*-
# from odoo import http


# class L10nCrExpenses(http.Controller):
#     @http.route('/l10n_cr_expenses/l10n_cr_expenses/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_cr_expenses/l10n_cr_expenses/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_cr_expenses.listing', {
#             'root': '/l10n_cr_expenses/l10n_cr_expenses',
#             'objects': http.request.env['l10n_cr_expenses.l10n_cr_expenses'].search([]),
#         })

#     @http.route('/l10n_cr_expenses/l10n_cr_expenses/objects/<model("l10n_cr_expenses.l10n_cr_expenses"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_cr_expenses.object', {
#             'object': obj
#         })
