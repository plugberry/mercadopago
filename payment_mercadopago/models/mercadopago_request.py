# -*- coding: utf-8 -*-
import logging

from odoo import _
from odoo.exceptions import UserError
from werkzeug import urls

_logger = logging.getLogger(__name__)

try:
    import mercadopago
    from mercadopago.config import RequestOptions
except ImportError:
    _logger.debug('Cannot import external_dependency mercadopago')


class MercadoPagoAPI():
    """ MercadoPago API integration.
    """

    def __init__(self, acquirer):
        request_options = RequestOptions(acquirer.mercadopago_access_token, platform_id="BVH38T5N7QOK0PPDGC2G")
        self.mp = mercadopago.SDK(acquirer.mercadopago_access_token, request_options=request_options)
        self.sandbox = not acquirer.state == "enabled"

    def check_response(self, resp):
        if resp['status'] in [200, 201]:
            return resp['response']
        elif resp['response'].get('cause'):
            return {
                'err_code': resp['response']['cause'][0].get('code'),
                'err_msg': resp['response']['cause'][0].get('description')
            }
        elif resp['response'].get('error'):
            return {
                'err_code': resp['response'].get('status', 0),
                'err_msg': resp['response'].get('error')
            }
        else:
            return {
                'err_code': 500,
                'err_msg': "Server Error"
            }

    # Preference
    def create_preference(self, preference):
        resp = self.mp.preference().create(preference)
        if self.sandbox:
            _logger.info('Preference Result:\n%s' % resp)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp['sandbox_init_point'] if self.sandbox else resp['init_point']

    # Customers
    def get_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.customer().search(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            try:
                customer_id = resp['results'][0].get('id')
            except IndexError:
                customer_id = self.create_customer_profile(email)
            return customer_id

    def create_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.customer().create(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp.get('id')

    # Cards
    def get_customer_cards(self, customer_id):
        resp = self.mp.card().list_all(customer_id)
        resp = self.check_response(resp)
        if type(resp) != list and resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def create_customer_card(self, customer_id, token):
        values = {
            "token": token
        }
        resp = self.mp.card().create(customer_id, values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def get_card_token(self, card_id):
        values = {
            "card_id": card_id
        }
        resp = self.mp.card_token().create(values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp['id']

    # Payments
    def payment(self, acquirer, token, amount, capture=True, cvv_token=None):
        """
        MercadoPago payment
        """
        values = {
            "token": cvv_token or self.get_card_token(token.token),
            "installments": token.installments,
            "transaction_amount": amount,
            "description": "Odoo ~ MercadoPago payment",
            "payment_method_id": token.acquirer_ref,
            "binary_mode": True,
            "payer": {
                "email": token.partner_id.email,
            },
            "notification_url": urls.url_join(acquirer.get_base_url(), "/payment/mercadopago/notification"),
            "capture": capture
        }
        if token.issuer:
            values.update(issuer_id=token.issuer)

        # TODO: revisar si deberíamos hacer esto directamente para todos los casos y ver si guardamos el dato antes
        if cvv_token or capture:
            customer_id = self.get_customer_profile(token.partner_id.email)
            values.update({"payer": {"type": 'customer', 'id': customer_id}})

        resp = self.mp.payment().create(values)
        if self.sandbox:
            _logger.info('Payment Result:\n%s' % resp)
        resp = self.check_response(resp)
        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def payment_cancel(self, payment_id):
        """
        MercadoPago cancelation payment
        """
        values = {
            "status": "cancelled"
        }

        resp = self.mp.payment().update(payment_id, values)
        resp = self.check_response(resp)
        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def get_payment(self, payment_id):
        resp = self.mp.payment().get(payment_id)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp
