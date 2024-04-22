# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MP POINT',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Payment method MP',
    'description': """
Allow to pay with MP POINT
==============================

This module allows customers to pay for their orders with credit
cards. The transactions are processed by MP (developed by Axcelere). 
    """,
    'depends': ['pos_mercadopago'],
    'data': [
        'views/mp_store_box_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'pos_mercadopago_point/static/src/js/PaymentScreen.js',
            'pos_mercadopago_point/static/src/js/CreditCardInstallmentButton.js',
        ],
    },
    'license': 'LGPL-3',
}
