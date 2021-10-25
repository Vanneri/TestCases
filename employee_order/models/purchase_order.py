# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends("move_ids.state", "move_ids.product_uom", "move_ids.product_uom_qty")
    def _compute_qty_to_receive(self):
        for line in self:
            total = 0.0
            for move in line.move_ids.filtered(
                    lambda m: m.state not in ("cancel", "done")
            ):
                if move.product_uom != line.product_uom:
                    total += move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom
                    )
                else:
                    total += move.product_uom_qty
            line.qty_to_receive = total

    qty_to_receive = fields.Float(
        compute="_compute_qty_to_receive",
        digits="Product Unit of Measure",
        copy=False,
        string="Qty to Receive",
        store=True,
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    emp_order_id = fields.Many2one(comodel_name='employee.order', string='Emp_order', required=False)

    def _compute_qty_to_receive(self):
        for po in self:
            qty_to_receive = sum(po.mapped("order_line.qty_to_receive"))
            po.pending_qty_to_receive = qty_to_receive > 0.0
            po.qty_to_receive = qty_to_receive

    @api.model
    def _search_pending_qty_to_receive(self, operator, value):
        if operator != "=" or not isinstance(value, bool):
            raise ValueError(_("Unsupported search operator"))
        po_line_obj = self.env["purchase.order.line"]
        po_lines = po_line_obj.search([("qty_to_receive", ">", 0.0)])
        orders = po_lines.mapped("order_id")
        if value:
            return [("id", "in", orders.ids)]
        else:
            return [("id", "not in", orders.ids)]

    qty_to_receive = fields.Float(
        compute="_compute_qty_to_receive",
        search="_search_qty_to_receive",
        string="Qty to Receive",
        default=0.0,
    )
    pending_qty_to_receive = fields.Boolean(
        compute="_compute_qty_to_receive",
        search="_search_pending_qty_to_receive",
        string="Pending Qty to Receive",
    )

    def _get_user_send_pickup_activities(self, user):
        domain = [
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('employee_order.mail_activity_send_pickup_date').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities

