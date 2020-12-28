# -*- coding: utf-8 -*-
import json
import logging
import requests

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.payment.models.payment_acquirer import _partner_split_name

_logger = logging.getLogger(__name__)

try:
    from mercadopago import mercadopago
except ImportError:
    _logger.debug('Cannot import external_dependency mercadopago')


class MercadoPagoAPI():
    """ MercadoPago API integration.
    """

    def __init__(self, acquirer):
        self.mp = mercadopago.MP(acquirer.mercadopago_access_token)
        self.mp.sandbox_mode(False) if acquirer.state == "prod" else self.mp.sandbox_mode(True)

    def check_response(self, resp):
        if resp['status'] in [200, 201]:
            return resp['response']
        elif resp['response'].get('cause'):
            return {
                'err_code': resp['response']['cause'][0].get('code'),
                'err_msg': resp['response']['cause'][0].get('description')
            }
        # TODO: siempre es un error 500?
        else:
            return {
                'err_code': 500,
                'err_msg': "Server Error"
            }

    # Customers
    def get_customer_profile(self, email):
        resp = self.mp.get('/v1/customers/search?%s' % email)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp['results'][0].get('id')

    def create_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.post('/v1/customers', values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp.get('id')

    # Cards
    def get_customer_cards(self, customer_id):
        resp = self.mp.get('/v1/customers/%s/cards' % customer_id)
        import pdb; pdb.set_trace()
        resp = self.check_response(resp)
        if type(resp) != list and resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def create_customer_card(self, customer_id, token):
        values = {
            "token": token
        }
        resp = self.mp.post('/v1/customers/%s/cards' % customer_id, values)
        resp = self.check_response(resp)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    # Payments

    def payment(self, token, amount, capture=True, cvv_token=None):
        """
        MercadoPago payment
        """
        values = {
                # este token puede ser:
                # - el primer token que devuelve MP si todavía no obtuvimos un card ID
                # - el card ID si estamos realizando un pago SIN CVV
                # - el CVV token si estamos realizando un pago CON CVV
                "token": cvv_token if cvv_token else token.token,
                "installments": 1,
                "transaction_amount": amount,
                "description": "Odoo ~ MercadoPago payment",
                "payment_method_id": token.acquirer_ref,
                "payer": {
                    "email": token.partner_id.email,
                },
                "capture": capture
            }
        if token.issuer:
            values.update(issuer_id=token.issuer)

        if cvv_token:
            # TODO: we should save this before?
            customer_id = self.get_customer_profile(token.partner_id)
            values.update({"payer": {"type": 'customer', 'id': customer_id}})
        resp = self.mp.post("/v1/payments", values)
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

        resp = self.mp.put("/v1/payments/" + payment_id, values)
        resp = self.check_response(resp)
        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp
