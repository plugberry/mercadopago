# -*- coding: utf-8 -*-
{
    'name': 'MercadoPago Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: MercadoPago Implementation',
    'version': '13.0.1.0.0',
    'description': """MercadoPago Payment Acquirer""",
    'depends': ['payment'],
    'external_dependencies': {
        'python': ['mercadopago'],
    },
    'data': [
        'views/payment_mercadopago_templates.xml',
        'views/payment_views.xml',
        'views/payment_transaction_views.xml',
        'views/assets.xml',
        'data/payment_acquirer_data.xml',
    ],
    'demo': [
        'demo/payment_acquirer_demo.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    # 'uninstall_hook': 'uninstall_hook'
}

