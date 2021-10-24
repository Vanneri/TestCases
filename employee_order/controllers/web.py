# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.main import Home
from odoo.http import request


class Home(Home):

    @http.route()
    def index(self, *args, **kw):
        user = request.env['res.users'].sudo().browse(request.session.uid)
        if request.session.uid and user.has_group('employee_order.group_user_internal'):
            return super(Home, self).index(*args, **kw)
        if request.session.uid and user.has_group('employee_order.group_user_employee'):
            return http.local_redirect('/my/emporder', query=request.params, keep_hash=True)
        if request.session.uid and user.has_group('employee_order.group_user_manager'):
            return http.local_redirect('/my/emporder', query=request.params, keep_hash=True)
        return super(Home, self).index(*args, **kw)

    def _login_redirect(self, uid, redirect=None):
        user = request.env['res.users'].sudo().browse(uid)
        if not redirect and user.has_group('employee_order.group_user_internal'):
            return super(Home, self)._login_redirect(uid, redirect=redirect)
        if not redirect and user.has_group('employee_order.group_user_employee'):
            redirect = '/my/emporder'
        if not redirect and user.has_group('employee_order.group_user_manager'):
            redirect = '/my/emporder'
        return super(Home, self)._login_redirect(uid, redirect=redirect)

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        user = request.env['res.users'].sudo().browse(request.session.uid)
        if request.session.uid and user.has_group('employee_order.group_user_internal'):
            return super(Home, self).web_client(s_action, **kw)
        if request.session.uid and user.has_group('employee_order.group_user_employee'):
            return http.local_redirect('/my/emporder', query=request.params, keep_hash=True)
        if request.session.uid and user.has_group('employee_order.group_user_manager'):
            return http.local_redirect('/my/emporder', query=request.params, keep_hash=True)
        return super(Home, self).web_client(s_action, **kw)

