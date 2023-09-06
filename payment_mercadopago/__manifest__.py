{
    'name': 'Mercado Pago Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: MercadoPago',
<<<<<<< HEAD
    'version': "16.0.3.0.0",
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
||||||| parent of 6ec746c (temp)
    'version': "15.0.1.3.3",
    'author': 'ADHOC SA - Axcelere S.A.S',
    'website': 'www.adhoc.com.ar, www.axcelere.com',
    'description': """MercadoPago Payment Acquirer""",
    'depends': ['payment'],
=======
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
    'depends': ['payment'],
>>>>>>> 6ec746c (temp)
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/payment_mercadopago_templates.xml',
        'wizards/check_payments.xml',
        'data/payment_acquirer_data.xml',
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
    'license': 'AGPL-3',
}
