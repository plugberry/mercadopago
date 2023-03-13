# -*- coding: utf-8 -*-
{
    'name': 'MercadoPago Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: MercadoPago',
<<<<<<< HEAD
    'version': "15.0.1.3.3",
    'author': 'ADHOC SA - Axcelere S.A.S',
    'website': 'www.adhoc.com.ar, www.axcelere.com',
||||||| parent of bbe24ce (temp)
    'version': '13.0.1.11.0',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
=======
    'version': '13.0.1.15.0',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
>>>>>>> bbe24ce (temp)
    'description': """MercadoPago Payment Acquirer""",
    'depends': ['payment'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'views/payment_views.xml',
<<<<<<< HEAD
        'views/payment_mercadopago_templates.xml',
||||||| parent of bbe24ce (temp)
        'views/payment_transaction_views.xml',
        'views/assets.xml',
=======
        'views/payment_transaction_views.xml',
        'views/assets.xml',
        'wizards/check_payments.xml',
>>>>>>> bbe24ce (temp)
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
