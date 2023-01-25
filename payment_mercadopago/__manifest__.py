# -*- coding: utf-8 -*-
{
    'name': 'Mercado Pago Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: MercadoPago',
<<<<<<< HEAD
    'version': "15.0.2.0.0",
    'description': """
Mercado pago Payment
===================
Mercadopago is the largest online payment platform in Latam.
This module integrates a checkout form and allows you to make payments through this payment gateway.
Supports automated payments without CVV for subscriptions and card authorizations.


    """,
    'author': 'Axadoo',
    'website': 'axadoo',
||||||| parent of 7d9c10b (temp)
    'version': '13.0.1.15.0',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'description': """MercadoPago Payment Acquirer""",
=======
    'version': '13.0.1.16.0',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'description': """MercadoPago Payment Acquirer""",
>>>>>>> 7d9c10b (temp)
    'depends': ['payment'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'views/payment_views.xml',
        'views/payment_mercadopago_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'demo': [
        'demo/payment_acquirer_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_mercadopago/static/src/scss/payment_mercadopago.scss',
            'payment_mercadopago/static/src/js/payment_form.js',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'application': False,
    'installable': True,
    'license': 'AGPL-3',
}
