# -*- coding: utf-8 -*-
{
    'name': 'MercadoPago Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: MercadoPago',
    'version': "15.0.1.3.3",
    'author': 'ADHOC SA - Axcelere S.A.S',
    'website': 'www.adhoc.com.ar, www.axcelere.com',
    'description': """MercadoPago Payment Acquirer""",
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
    'license': 'LGPL-3',
}
