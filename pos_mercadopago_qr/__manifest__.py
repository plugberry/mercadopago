# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MP QR',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Payment method MP',
    'description': """
Allow to pay with MP QR
==============================

This module allows customers to pay for their orders with credit
cards. The transactions are processed by MP (developed by Axcelere). 
    """,
    'depends': ['pos_mercadopago'],
    'data': [
        # 'views/pos_config_setting_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'pos_mercadopago_qr/static/src/js/PaymentScreen.js',
            'pos_mercadopago_qr/static/src/js/CreditCardInstallmentButton.js',
        ],
    },
    'license': 'LGPL-3',
}
