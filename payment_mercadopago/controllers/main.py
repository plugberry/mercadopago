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
                [
                ('provider', '=', 'mercadopago')], limit=1
            ) or False
        }

       )
       return res

    @http.route(['/process_payment'], type='http',
                auth='public')
    def payment_mercadogo_result(self, **kwargs):
        print(kwargs)

        #  transaction_id = request.env['payment.transaction'].sudo().search(
            #  [
                #  ('reference',  '=', 'Test de pago')
            #  ], limit=1
        #  )
        #  if not transaction_id:
            #  transaction_id = request.env['payment.transaction'].sudo().create(
                #  {
                    #  'reference': 'Test1 de pago',
                    #  'amount': 1,
                    #  'return_url': '/shop/payment/validate',
                    #  'acquirer_id': int(kwargs.get('acquired_id')),
                    #  'date': fields.Datetime.now(),
                    #  'state': 'draft',
                    #  'currency_id': request.env.user.currency_id.id,
                #  }
            #  )
        #  PaymentProcessing.add_payment_transaction(transaction_id)
        mp = mercadopago.MP(
            'TEST-1709591807623095-092515-b72afcae8c34385b6f192949928b68fb-651063263'
        )

        payment_id = request.env['payment.acquirer'].browse(
            int(kwargs.get('acquired_id')))
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
            payment_token = request.env[
                    'payment.token'].sudo()
            cards_result = mp.get('/v1/customers/%s/cards' % exist_customer)
            response = cards_result.get('response')
            if len(response) and cards_result.get('status') != 404:
                for card in response:
                    if not payment_token.search(
                        [
                            ('card_id', '=', card.get('id')                            )
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


        #  payment_data = {
            #  "token": kwargs.get('token'),
            #  "installments":  int(kwargs.get('installments')),
            #  "transaction_amount":100,
            #  "description": "Point Mini a maquininha que dá o dinheiro de suas vendas na hora",
            #  "payment_method_id": kwargs.get('paymentMethodId'),
            #  "payer": {
                #  "email": kwargs.get('email'),
            #  }
        #  }
        #  payment_result = mp.post("/v1/payments", payment_data)
#
#
        #  if payment_result.get('status') == 201:
            #  response = payment_result.get('response')
            #  if response['status'] == 'approved':
                #  card_name = response['card']['first_six_digits'] \
                            #  + 'XXXXXX' \
                            #  + response['card']['last_four_digits']
                #  payment_token = request.env[
                    #  'payment.token'].sudo().mercadopago_create_payment_token(
                    #  card_name,
                    #  request.env.user.partner_id.id,
                    #  issuer_id,
                    #  installments,
                    #  payment_method_id,
                    #  token_card,
                    #  payment_id)
                #  if not payment_token:
                    #  res = {
                        #  'result': False,
                        #  'error': _(
                            #  'The transaction could not be generated in our e-commerce')
                    #  }
                    #  return res
                #  transaction_id.state = 'done'
            #  else:
                #  res = {
                    #  'result': False,
                    #  'error': _(
                        #  'The transaction could not be generated in our e-commerce')
                #  }


    @http.route(['/payment/existing_card/mercadopago'], type='json',
                auth='public')
    def find_existing_mercadopago_card(self, **kwargs):
        pm_id = kwargs.get('token_id', False)
        request.session.update(kwargs)
        request.session.update({'payment_id': int(kwargs.get('acquirer_id'))})

        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/shop/?error=invalid_token_id')

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
        mp = mercadopago.MP(
            'TEST-3834170027218729-082509-763e2577356637318da741a535bf25ec-628558216'
        )
        payment_data = {
            "token": token_card,
            "installments": installments,
            "transaction_amount": order_id.amount_total,
            "description": "Point Mini a maquininha que dá o dinheiro de suas vendas na hora",
            "payment_method_id": payment_method_id,
            "issuer_id": issuer_id,
            "payer": {
                "email": payment_token.partner_id.email,
            }
        }

        payment_result = mp.post("/v1/payments", payment_data)
        if payment_result.get('status') == 201:
            response = payment_result.get('response')
            if response['status'] == 'approved':
                order_id.action_confirm()
                transaction_id.state = 'done'
            else:
                print(payment_result)
                res = {
                    'result': False,
                    'error': _(
                        'The transaction could not be generated in our e-commerce')
                }
                return res
        else:
            msg = payment_result.get('response').get('message')
            res = {
                'result': False,
                'error': _(msg)
            }
            return res
        return request.redirect('/payment/process')

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
        # values = {
        #     'acquirer_id': int(kwargs.get('acquirer_id')),
        #     'partner_id': int(kwargs.get('partner_id')),
        #     'acquirer_ref': uuid4(),
        # }
        # pm_id = request.env['payment.token'].search(
        #     [('partner_id', '=', int(kwargs.get('partner_id'))),
        #     ('acquirer_id', '=', int(kwargs.get('acquirer_id')))])
        # if not pm_id:
        #     payment_token = request.env['payment.token'].sudo().create(values)
        # else:
        #     payment_token = pm_id
        # vals = {
        #     'pm_id': payment_token.id
        # }
        order_id = request.website.sale_get_order()
        partner_id = int(kwargs.get('partner_id'))
        payment_id = request.env['payment.acquirer'].browse(
            int(kwargs.get('acquirer_id')))
        issuer_id = kwargs.get('issuer_id', False) and \
                    int(kwargs.get('issuer_id', False)) or False
        installments = kwargs.get('installments') and \
                       int(kwargs.get('installments')) or False
        payment_method_id = kwargs.get('payment_method_id')
        token_card = kwargs.get('token')
        # payment_token = request.env[
        #     'payment.token'].sudo().mercadopago_create_payment_token(
        #     partner_id, customer, card_mercadopago, payment_id)
        transaction_id = request.env['payment.transaction'].sudo().search(
            [
                ('reference',  '=', order_id.name)
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
        # transaction_id.confirm_sale_token(order)
        PaymentProcessing.add_payment_transaction(transaction_id)
        mp = mercadopago.MP(
            'TEST-3834170027218729-082509-763e2577356637318da741a535bf25ec-628558216'
        )
        payment_data = {
            "token": kwargs.get('token'),
            "installments": installments,
            "transaction_amount": float(kwargs.get('order_amount')),
            "description": "Point Mini a maquininha que dá o dinheiro de suas vendas na hora",
            "payment_method_id": kwargs.get('payment_method_id'),
            "issuer_id": issuer_id,
            "payer": {
                "email": "test_user_123456@testuser.com",
            }
        }
        payment_result = mp.post("/v1/payments", payment_data)
        if payment_result.get('status') == 201:
            response = payment_result.get('response')
            if response['status'] == 'approved':
                card_name = response['card']['first_six_digits'] \
                            + 'XXXXXX' \
                            + response['card']['last_four_digits']
                payment_token = request.env[
                    'payment.token'].sudo().mercadopago_create_payment_token(
                    card_name,
                    partner_id,
                    issuer_id,
                    installments,
                    payment_method_id,
                    token_card,
                    payment_id)
                if not payment_token:
                    res = {
                        'result': False,
                        'error': _(
                            'The transaction could not be generated in our e-commerce')
                    }
                    return res
                order_id.action_confirm()
                transaction_id.state = 'done'
            else:
                res = {
                    'result': False,
                    'error': _(
                        'The transaction could not be generated in our e-commerce')
                }
                return res

        # return request.redirect(
        #     '/shop/payment/token?%s' % urllib.parse.urlencode(vals)
        # )
        return request.redirect('/payment/process')


class MercadoPagoController(http.Controller):
    _success_url = '/payment/mercadopago/success/'
    _pending_url = '/payment/mercadopago/pending/'
    _failure_url = '/payment/mercadopago/failure/'
    # _notify_url = '/payment/mercadopago/notify/'
    _create_preference_url = '/payment/mercadopago/create_preference'

    @http.route([
        '/payment/mercadopago/create_preference',
    ],
        type='http', auth="none", csrf=False)
    def mercadopago_create_preference(self, **post):
        # TODO podriamos pasar cada elemento por separado para no necesitar
        # el literal eval
        mercadopago_data = safe_eval(post.get('mercadopago_data', {}))
        acquirer = request.env['payment.acquirer'].browse(mercadopago_data.get('acquirer_id')).sudo()
        if not acquirer:
            return werkzeug.utils.redirect("/")

        environment = mercadopago_data.get('environment')
        mercadopago_preference = mercadopago_data.get(
            'mercadopago_preference')
        mercadopago_client_id = acquirer.mercadopago_client_id
        mercadopago_secret_key = acquirer.mercadopago_secret_key
        if (
                not environment or
                not mercadopago_preference or
                not mercadopago_secret_key or
                not mercadopago_client_id
        ):
            _logger.warning('Missing parameters!')
            return werkzeug.utils.redirect("/")
        MPago = mercadopago.MP(
            mercadopago_client_id, mercadopago_secret_key)
        if environment == "prod":
            MPago.sandbox_mode(False)
        else:
            MPago.sandbox_mode(True)
        preferenceResult = MPago.create_preference(mercadopago_preference)
        if environment != "prod":
            _logger.info('Preference Result: %s' % preferenceResult)

        # # TODO validate preferenceResult response
        if environment == "prod":
            linkpay = preferenceResult['response']['init_point']
        else:
            linkpay = preferenceResult['response']['sandbox_init_point']

        return werkzeug.utils.redirect(linkpay)

    @http.route([
        '/payment/mercadopago/success',
        '/payment/mercadopago/pending',
        '/payment/mercadopago/failure'
    ],
        type='http', auth="none",
        # csrf=False,
    )
    def mercadopago_back_no_return(self, **post):
        """
        Odoo, si usas el boton de pago desde una sale order o email, no manda
        una return url, desde website si y la almacenan en un valor que vuelve
        desde el agente de pago. Como no podemos mandar esta "return_url" para
        que vuelva, directamente usamos dos distintas y vovemos con una u otra
        """
        _logger.info(
            'Mercadopago: entering mecadopago_back with post data %s',
            pprint.pformat(post))
        request.env['payment.transaction'].sudo().form_feedback(
            post, 'mercadopago')
        return werkzeug.utils.redirect("/payment/process")
