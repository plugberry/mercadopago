##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
import pprint
import werkzeug
from odoo import http, fields, _
import urllib.request
import urllib
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
from uuid import uuid4
import json
from datetime import datetime
from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)
try:
    from mercadopago import mercadopago
except ImportError:
    _logger.debug('Cannot import external_dependency mercadopago')


from odoo.addons.website_sale.controllers.main import WebsiteSale


class ExtendedWebsiteSale(WebsiteSale):
    def _get_shop_payment_values(self, order, **kwargs):
        res = super(ExtendedWebsiteSale, self)._get_shop_payment_values(
                order, **kwargs
        )
        res.update(
            {
                'mercadopago': request.env['payment.acquirer'].sudo().search(
                    [('provider', '=', 'mercadopago')], limit=1
                ) or False
            }
        )
        return res

    @http.route(['/process_payment'], type='http',
                auth='public')
    def payment_mercadogo_result(self, **kwargs):
        payment_id = request.env['payment.acquirer'].browse(
            int(kwargs.get('acquired_id')))
        mp = mercadopago.MP(payment_id.mercadopago_secret_key)
        issuer_id = kwargs.get('issuer_id', False) and \
                    int(kwargs.get('issuer_id', False)) or False
        installments = kwargs.get('installments') and \
                       int(kwargs.get('installments')) or False
        payment_method_id = kwargs.get('paymentMethodId')
        token_card = kwargs.get('token')
        # Crear customer
        partner_id = request.env.user.partner_id
        existing_customer = mp.get('/v1/customers/search')
        exist_customer = False

        def create_card(token, mp_id):
            card_data = {
                "token": token 
            }
            card_result = mp.post('/v1/customers/%s/cards' % mp_id, card_data)
            return card_result

        if 'response' in existing_customer:
            if not partner_id.mp_id:
                # TODO: Hacer esto con comprension de listo
                for cust in existing_customer.get('response').get('results'):
                    if not cust.get('email') == partner_id.email:
                        exist_customer = False
                    else:
                        exist_customer = cust.get('id')
                        break
            else:
                exist_customer = partner_id.mp_id
        if not exist_customer:
            customer_data = {
                    "email": partner_id.email,
                    "first_name": partner_id.name,
                    "last_name": partner_id.lastname,
                    "identification": {
                        "type": kwargs.get('docType'),
                        "number": kwargs.get('docNumber')
                        },
                    "address": {
                        "zip_code": partner_id.zip,
                        "street_name": partner_id.street,
                        },
                    "description": "Creacion de cliente"                
            }
            customer_result = mp.post('/v1/customers', customer_data)
            if customer_result.get('status') == 201:
                response = customer_result.get('response')
                mp_id = response.get('id')
                partner_id.mp_id = mp_id

                # Creando la tarjeta y tokenizandola
                cards_result = mp.get('/v1/customers/%s/cards' % mp_id)
                create_card(kwargs.get('token'), mp_id)
        else:
            # Creando la tarjeta y tokenizandola
            partner_id.mp_id = exist_customer
            payment_token = request.env['payment.token'].sudo()
            cards_result = mp.get('/v1/customers/%s/cards' % exist_customer)
            response = cards_result.get('response')
            if len(response) and cards_result.get('status') != 404:
                for card in response:
                    if not payment_token.search(
                        [
                            ('card_id', '=', card.get('id'))
                        ]
                    ):
                        card_name =card['first_six_digits'] \
                                + 'XXXXXX' \
                                + card['last_four_digits']
                        payment_token.mercadopago_create_payment_token(
                            card_name,
                            request.env.user.partner_id.id,
                            issuer_id,
                            installments,
                            payment_method_id,
                            kwargs.get('token'),
                            payment_id,
                            card_id=card.get('id'))
            else:
                card_result = create_card(kwargs.get('token'), exist_customer)
                card = card_result.get('response')
                card_name = card['first_six_digits'] \
                        + 'XXXXXX' \
                        + card['last_four_digits']
                payment_token.mercadopago_create_payment_token(
                    card_name,
                    request.env.user.partner_id.id,
                    issuer_id,
                    installments,
                    payment_method_id,
                    kwargs.get('token'),
                    payment_id,
                    card_id=card.get('id'))

        return http.redirect_with_hash('/my/payment_method')

    @http.route(['/payment/existing_card/mercadopago'], type='json',
                auth='public')
    def find_existing_mercadopago_card(self, **kwargs):
        pm_id = kwargs.get('token_id', False)
        request.session.update(kwargs)
        request.session.update({'payment_id': int(kwargs.get('acquirer_id'))})

        try:
            pm_id = int(pm_id)
        except ValueError:
            return werkzeug.utils.redirect('/shop/?error=invalid_token_id')

        payment_token = request.env['payment.token'].browse(pm_id)
        payment_id = payment_token.acquirer_id

        order = request.session.sale_order_id
        order_id = request.env['sale.order'].sudo().browse(order)
        partner_id = payment_token.partner_id.id
        issuer_id = payment_token.issuer_id
        installments = payment_token.installments
        payment_method_id = payment_token.payment_method_id
        token_card = payment_token.token_card

        transaction_id = request.env['payment.transaction'].sudo().search(
            [
                ('reference', '=', order_id.name)
            ], limit=1
        )

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
        PaymentProcessing.add_payment_transaction(transaction_id)
        mp = mercadopago.MP(payment_id.mercadopago_secret_key)
        payment_data = {
            "token": token_card,
            "installments": installments,
            "transaction_amount": order_id.amount_total,
            "description": "Point Mini a maquininha que dá o dinheiro de suas "
                           "vendas na hora",
            "payment_method_id": payment_method_id,
            "payer": {
                "email": payment_token.partner_id.email,
            }
        }
        if issuer_id:
            payment_data.update(issuer_id=issuer_id)

        payment_result = mp.post("/v1/payments", payment_data)
        if payment_result.get('status') == 201:
            response = payment_result.get('response')
            if response['status'] == 'approved':
                order_id.action_confirm()
                transaction_id.state = 'done'
            else:
                res = {
                    'result': False,
                    'error': _('The transaction could not be generated in our '
                               'e-commerce')
                }
                return res
        else:
            msg = payment_result.get('response').get('message')
            res = {
                'result': False,
                'error': _(msg)
            }
            return res
        return werkzeug.utils.redirect('/payment/process')
