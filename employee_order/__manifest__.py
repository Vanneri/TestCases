# -*- coding: utf-8 -*-
{
    'name': "Employee Order",

    'summary': """For managing Employee Order""",

    'category': 'Inventory/Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase_stock', 'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_activity_data.xml',
        'wizard/send_pickup_date.xml',
        'views/employee_order.xml',
        'views/purchase_order_view.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
}
