{
    'name': 'Mercado Pago Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: MercadoPago',
    'version': "16.0.4.5.0",
    'description': """
Mercado pago Payment
===================
Mercadopago is the largest online payment platform in Latam.
This module integrates a checkout form and allows you to make payments through this payment gateway.
Supports automated payments without CVV for subscriptions and card authorizations.


    """,
    'author': 'Plugberry',
    'website': 'www.plugberry.com',
    'sequence': 350,
    'depends': ['payment', 'account'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/payment_mercadopago_templates.xml',
        'wizards/check_payments.xml',
        'data/payment_acquirer_data.xml',
        'data/ir_cron.xml',
    ],
    'demo': [
        'demo/payment_acquirer_demo.xml',
    ],
    'images':  ['static/description/odoomp.png'],
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
