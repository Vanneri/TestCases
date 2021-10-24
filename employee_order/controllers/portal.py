from ast import literal_eval
from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
import base64


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        EmployeeOrder = request.env['employee.order']
        if 'order_count' in counters:
            values['order_count'] = EmployeeOrder.search_count([
                ('state', 'in', ['draft', 'approved', 'purchase_in_progress', 'ready_to_pick', 'done', 'rejected'])
            ]) if EmployeeOrder.check_access_rights('read', raise_exception=False) else 0
        return values

    def _employee_order_get_page_view_values(self, order, access_token, **kwargs):
        manager = True
        if not request.env.user.has_group('base.group_erp_manager'):
            manager = False
        values = {
            'employee_order': order,
            'token': access_token,
            'partner_id': order.partner_id.id,
            'report_type': 'html',
            'manager': manager
        }
        if order.company_id:
            values['res_company'] = order.company_id
        history = request.session.get('my_orders_history', [])
        values.update(get_records_pager(history, order))
        return values

    def _prepare_portal_emp_values(self):

        return {
            'page_name': 'home',
        }

    @http.route(['/my/emporder', '/my/emporder/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_employee_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        EmployeeOrder = request.env['employee.order']
        manager = True
        domain = [
            ('state', 'in', ['draft', 'approved', 'purchase_in_progress', 'ready_to_pick', 'done', 'rejected'])

        ]
        if not request.env.user.has_group('base.group_erp_manager'):
            manager = False
            domain += [('user_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = EmployeeOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/emporder",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        orders = EmployeeOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'employeeorder',
            'pager': pager,
            'default_url': '/my/emporder',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'manager': manager
        })
        return request.render("employee_order.portal_my_employee_orders", values)

    @http.route(['/my/emporder/<int:order_id>'], type='http', auth="public", website=True)
    def portal_employee_order_page(self, order_id, report_type=None, access_token=None, message=False, download=False,
                                   **kw):
        try:
            order_sudo = self._document_check_access('employee.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._employee_order_get_page_view_values(order_sudo, access_token, **kw)
        values['message'] = message
        return request.render('employee_order.employee_order_portal_template', values)

    @http.route(['/my/emporder/create'], type='http', auth="user", website=True)
    def portal_create_employee_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **post):
        values = self._prepare_portal_emp_values()
        user = request.env.user
        partner = request.env.user.partner_id
        products = []
        suppliers = []
        tax_ids = False
        employee_config = request.env['employee.order.config'].sudo().search([('user_id', '=', user.id)])
        if employee_config:
            products = request.env['product.product'].sudo().search(
                [('categ_id', 'child_of', employee_config.categ_id.id)])
            tax_ids = employee_config.taxes_id

        if post and request.httprequest.method == 'POST':
            EmployeeOrder = request.env['employee.order']
            Attachments = request.env['ir.attachment']
            tax_ids = []
            taxes_id = literal_eval(post['taxes_id'])
            product_detail = request.env['product.product'].sudo().search([('id', '=', int(post['product_id']))])
            if taxes_id:
                tax_ids = request.env['account.tax'].sudo().search([('id', 'in', taxes_id)])
            attachment_name = post.get('attachment').filename
            file = post.get('attachment')
            try:
                employee_order = EmployeeOrder.create({
                    'product_id': int(post['product_id']),
                    'partner_id': int(post['supplier']),
                    'price_unit': float(post['supplier_id']),
                    'product_qty': post['qty'],
                    'taxes_id': [(6, 0, tax_ids.ids)] if tax_ids else False,
                })
            except:
                return {'error': _('Error Occurred.')}
            if employee_order:
                Attachments.sudo().create({
                    'name': attachment_name,
                    'res_name': attachment_name,
                    'type': 'binary',
                    'res_model': 'employee.order',
                    'res_id': employee_order.id,
                    'datas': base64.b64encode(file.read()),
                })
                msg = _(
                    'Dear %s , the employee %s has requested the following product %s . Please, check the order') % (
                          employee_config.sudo().employee_id.parent_id.name, employee_config.employee_id.name,
                          product_detail.name)
                _message_post_helper(
                        'employee.order', employee_order.id, msg, token=employee_order.sudo().access_token,
                    partner_ids=employee_config.sudo().employee_id.parent_id.sudo().user_id.sudo().partner_id.ids)

        values = {
            'partner': partner,
            'products': products,
            'suppliers': suppliers,
            'tax_ids': tax_ids,
            'is_custom_tax': True if tax_ids else False,
            'page_name': 'create_emp_order',
        }
        return request.render('employee_order.employee_order_portal_create', values)

    @http.route(['/my/emporder/<int:order_id>/accept'], type='http', auth="public", website=True)
    def portal_employee_order_accept(self, order_id, access_token=None):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('employee.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        order_sudo.action_confirm()
        msg = _(
            'Dear %s , your order have been approved. Please go to your order and click on the button Buy product') % (
                  order_sudo.user_id.name)
        _message_post_helper(
            'employee.order', order_sudo.id, msg,
            **({'token': access_token} if access_token else {}))

        return request.redirect('/my/emporder')

    @http.route(['/my/emporder/<int:order_id>/reject'], type='http', auth="public", website=True)
    def portal_employee_order_reject(self, order_id, access_token=None):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('employee.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        order_sudo.action_reject()
        msg = _('Dear %s , sadly your order was rejected for this month, but you can create a new one for the same '
                'product or a different one next month.Regards') % (order_sudo.user_id.name)
        _message_post_helper(
            'employee.order', order_sudo.id, msg,
            **({'token': access_token} if access_token else {}))

        return request.redirect('/my/emporder')

    @http.route(['/my/emporder/<int:order_id>/buypro'], type='http', auth="public", website=True)
    def portal_employee_order_reject(self, order_id, access_token=None):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('employee.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        order_sudo.action_buy_pro()

        return request.redirect('/my/emporder')
