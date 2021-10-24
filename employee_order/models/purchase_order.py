from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    emp_order_id = fields.Many2one(
        comodel_name='employee.order',
        string='Emp_order',
        required=False)
