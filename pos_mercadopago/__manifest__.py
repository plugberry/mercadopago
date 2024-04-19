# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MP',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Payment method MP',
    'description': """
Allow to pay with MP
==============================

This module allows customers to pay for their orders with credit
cards. The transactions are processed by MP (developed by Axcelere). 
    """,
    'depends': ['point_of_sale', 'pos_credit_card_installment'],
    'data': [
        'security/ir.model.access.csv',
        'views/mp_credential_views.xml',
        'views/mp_store_views.xml',
        'views/mp_store_box_views.xml',
        'views/mp_log_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
