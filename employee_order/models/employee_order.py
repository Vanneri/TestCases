# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class EmployeeOrder(models.Model):
    _name = 'employee.order'
    _description = 'Employee Order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
        'purchase_in_progress': [('readonly', True)],
        'ready_to_pick': [('readonly', True)],
        'done': [('readonly', True)],
    }

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        """
        Compute the amounts of the Emp Order.
        """
        for order in self:
            price = order.price_unit
            taxes = order.taxes_id.compute_all(price, order.currency_id, order.product_qty,
                                               product=order.product_id, partner=order.partner_id)
            order.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True, states=READONLY_STATES, )
    date_order = fields.Datetime('Order Deadline', required=True, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Depicts the date within which the Quotation should be confirmed and converted "
                                      "into a purchase order.", states=READONLY_STATES, )
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, change_default=True, tracking=True,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.",
                                 states=READONLY_STATES, )
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price', states=READONLY_STATES, )
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True,
                               states=READONLY_STATES, )
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  related='product_id.uom_id')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)], states=READONLY_STATES, )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('purchase_in_progress', 'Purchase in progress'),
        ('ready_to_pick', 'Ready to pick-up'),
        ('done', 'Done'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    user_id = fields.Many2one(
        'res.users', string='User', index=True, tracking=2, default=lambda self: self.env.user)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', compute='_compute_attachment',
                                      compute_sudo=True)
    attachment_counts = fields.Integer(string='Attachment Counts', compute='_compute_attachment', store=True,
                                       compute_sudo=True)
    order_ids = fields.One2many(comodel_name='purchase.order', inverse_name='emp_order_id', string='Orders')

    def _compute_attachment(self):
        for order in self:
            if order.ids:
                order.attachment_ids = self.env['ir.attachment'].search([
                    ('res_model', '=', 'employee.order'),
                    ('res_id', '=', order.id),
                ])
                order.attachment_counts = len(order.attachment_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.order') or _('New')
        result = super(EmployeeOrder, self).create(vals)
        return result

    def _compute_access_url(self):
        super(EmployeeOrder, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/emporder/%s' % (order.id)

    def _create_po(self):
        Purchase = self.env['purchase.order']
        for order in self:
            Purchase.create({
                'partner_id': order.partner_id.id,
                'emp_order_id': order.id,
                'order_line': [(0, 0, {
                    'product_id': order.product_id.id,
                    'product_qty': order.product_qty,
                    'price_unit': order.price_unit,
                    'taxes_id': [(6, 0, order.taxes_id.ids)]
                })]
            })

    def action_confirm(self):
        for order in self:
            order.write({'state': 'approved'})

    def action_reject(self):
        for order in self:
            order.write({'state': 'rejected'})

    def action_buy_pro(self):
        for order in self:
            order._create_po()
            order.write({'state': 'purchase_in_progress'})

    def action_done(self):
        for order in self:
            order.write({'state': 'done'})

    def action_view_po(self):
        orders = self.mapped('order_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_form_action")
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        elif len(orders) == 1:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = orders.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class EmployeeOrderConfig(models.Model):
    _name = 'employee.order.config'
    _description = 'Employee Order Configuration'
    _rec_name = 'employee_id'

    READONLY_STATES = {
        'done': [('readonly', True)],
    }

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, states=READONLY_STATES)
    product_qty = fields.Float(string='Max Quantity', digits='Product Unit of Measure', required=True,
                               states=READONLY_STATES, default=3.0)
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)], states=READONLY_STATES)
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True,
        required=True, help="Select category", states=READONLY_STATES)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    user_id = fields.Many2one(
        comodel_name='res.users', related='employee_id.user_id',
        string='User',
        required=False)
    employee_parent_id = fields.Many2one('hr.employee', 'Manager', related='employee_id.parent_id')
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'), ],
        required=False, default='draft')

    def action_confirm(self):
        self.write({'state': 'done'})

    @api.constrains('employee_id', 'company_id')
    def _check_unique_config(self):
        domain = [('employee_id', 'in', self.employee_id.ids),
                  ('company_id', 'in', self.company_id.ids)]
        fields = ['company_id', 'employee_id']
        groupby = ['company_id', 'employee_id']
        records = self.read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                employee_name = self.env['hr.employee'].browse(rec['employee_id'][0]).display_name
                error_message_lines.append(_(" - Configuration for Employee: %s Already Done", employee_name))
        if error_message_lines:
            raise ValidationError(_(
                'Configuration Duplication Occurs:\n') + '\n'.join(
                error_message_lines))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        if not self.employee_id.user_id:
            raise UserError(_('Assign Related User For %s.', self.employee_id.name))
        if not self.employee_id.parent_id:
            raise UserError(_('Assign Manager For %s.', self.employee_id.name))
        else:
            if not self.employee_id.parent_id.user_id:
                raise UserError(_('Manager should linked with User For %s.', self.employee_id.parent_id.name))


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    def name_get(self):
        res = []
        for info in self:
            name = info.name or ''
            if self._context.get('show_price'):
                name = "%s ‒ %s" % (info.name.name, info.price)
            res.append((info.id, name))
        return res
