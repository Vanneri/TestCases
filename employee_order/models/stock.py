# -*- coding: utf-8 -*-

from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        if self.picking_type_id and self.picking_type_id.code == 'incoming':
            if self.purchase_id and self.purchase_id.emp_order_id and self.purchase_id.qty_to_receive == 0.0:
                self.purchase_id.activity_schedule(
                    'employee_order.mail_activity_send_pickup_date', fields.Date.today(),
                    summary=_('Send Pickup Date'), user_id=self.env.user.id)
        return res
