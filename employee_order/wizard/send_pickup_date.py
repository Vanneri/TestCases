# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class SendPickupDate(models.TransientModel):
    _name = 'order.send.pick.update'
    _description = 'Send Pick Up Date'

    pickup_date = fields.Date(string='Pickup date')

    def send_mail(self):
        purchase_orders = self.env['purchase.order'].browse(self._context.get('active_ids', []))
        for order in purchase_orders:
            if order.emp_order_id.filtered(lambda e: e.state not in ('ready_to_pick', 'done')):
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                if not float_is_zero(order.qty_to_receive, precision_digits=precision):
                    raise UserError(_("Order is not fully received to send pickup date"))
                body = (_('<p>Dear <a href=# data-oe-model=res.users data-oe-id=%d>@%s</a> ,') % (
                    order.emp_order_id.user_id.id, order.emp_order_id.user_id.name))
                body += (_('\nYour product %s from the order %s is ready.') % (
                    order.emp_order_id.product_id.name, order.emp_order_id.name))
                body += (_('\n You can pick it at the office on %s. Regards') % self.pickup_date)
                order.emp_order_id.message_post(body=body,
                                                partner_ids=order.emp_order_id.mapped('user_id.partner_id').ids,
                                                message_type="notification", subtype_xmlid="mail.mt_note", )
                order.emp_order_id.write({'state': 'ready_to_pick'})
                order.sudo()._get_user_send_pickup_activities(user=self.env.user).action_feedback()
