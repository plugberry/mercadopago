{
    'name': 'MercadoPago Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: MercadoPago',
    'version': "15.0.1.0.0",
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'description': """MercadoPago Payment Acquirer""",
    'depends': ['payment'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'views/payment_mercadopago_templates.xml',
        'views/payment_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'demo': [
        'demo/payment_acquirer_demo.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    # 'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_adyen/static/src/js/payment_form.js',
        ],
    },
}
