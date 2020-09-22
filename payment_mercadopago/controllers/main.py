##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
import pprint

import werkzeug
from odoo import http, fields
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
try:
    from mercadopago import mercadopago
except ImportError:
    _logger.debug('Cannot import external_dependency mercadopago')

from odoo.addons.website_sale.controllers.main import WebsiteSale


class ExtendedWebsiteSale(WebsiteSale):

    @http.route(
        '/shop/payment/mercadopago',
        type='http',
        auth='public',
        website=True,
        sitemap=False
    )
    def mercadopago(self, **kwargs):
        """ Method that handles payment using saved tokens
            :param int pm_id: id of the payment.token that we want to use
        """
        order_id = request.website.sale_get_order()
        partner_id = int(kwargs.get('partner_id'))
        payment_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        transaction_id = request.env['payment.transaction'].sudo().search([('reference', '=', order_id.name)], limit=1)
        if not transaction_id:
            transaction_id = request.env['payment.transaction'].sudo().create(
                {
                    'reference': order_id.name,
                    'sale_order_ids': [(4, order_id.id, False)],
                    'amount': order_id.amount_total,
                    'return_url': '/shop/payment/validate',
                    'currency_id': order_id.currency_id.id,
                    'partner_id': partner_id,
                    'acquirer_id': payment_id.id,
                    'date': fields.Datetime.now(),
                    'state': 'draft',
                }
            )
        # transaction_id.confirm_sale_token(order)
        PaymentProcessing.add_payment_transaction(transaction_id)
        mp = mercadopago.MP('TEST-6cb31e18-4db7-45c5-8035-d8b20a2d899e')
        payment_data = {
            "token": kwargs.get('token'),
            "installments": int(kwargs.get('installments')),
            "transaction_amount": float(kwargs.get('order_amount')),
            "description": "Point Mini a maquininha que dá o dinheiro de suas vendas na hora",
            "payment_method_id": kwargs.get('payment_method_id'),
            "issuer_id": int(kwargs.get('issuer_id')),
            "payer": {
                "email": "test_user_123456@testuser.com",
            }
        }
        payment_result = mp.post("/v1/payments", payment_data)
        if payment_result.get('status') == 201:
            response = payment_result.get('response')
            if response['status'] == 'approved':
                order_id.action_confirm()
                transaction_id.state = 'done'

        # return request.redirect(
        #     '/shop/payment/token?%s' % urllib.parse.urlencode(vals)
        # )
        return request.redirect('/payment/process')
