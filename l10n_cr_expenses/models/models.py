# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class l10n_cr_expenses(models.Model):
#     _name = 'l10n_cr_expenses.l10n_cr_expenses'
#     _description = 'l10n_cr_expenses.l10n_cr_expenses'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
