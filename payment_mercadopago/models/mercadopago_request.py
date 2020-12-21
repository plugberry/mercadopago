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

    # Customers
    def get_customer_profile(self, email):
        resp = self.mp.get('/v1/customers/search?%s' % email)
        # TODO: improve check status
        if 'response' in resp and resp['response']['results']:
            return resp['response']['results'][0]['id']

    def create_customer_profile(self, email):
        values = {'email': email}
        resp = self.mp.post('/v1/customers', values)
        # if resp and resp.get('err_code'):
        #     raise UserError(_(
        #         "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return resp.get('id')

    # Cards
    def get_customer_cards(self, customer_id):
        resp = self.mp.get('/v1/customers/%s/cards' % customer_id)
        # TODO: improve check status
        if 'response' in resp:
            return resp['response']

    def create_customer_card(self, customer_id, token):
        values = {
            "token": token
        }
        resp = self.mp.post('/v1/customers/%s/cards' % customer_id, values)

        # if resp and resp.get('err_code'):
        #     raise UserError(_(
        #         "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return resp['response']

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
        # if issuer_id:
        #         payment_data.update(issuer_id=issuer_id)

        if cvv_token:
            # TODO: we should save this before?
            customer_id = self.get_customer_profile(token.partner_id)
            values.update({"payer": {"type": 'customer','id': customer_id}})

        resp = self.mp.post("/v1/payments", values)
        if resp['status'] == 201:
            return resp['response']


    def payment_cancel(self, payment_id):
        """
        MercadoPago cancelation payment
        """
        values = {
                "status": "cancelled"
            }

        # access_token = self.mp.customer.get_access_token()
        resp = self.mp.put("/v1/payments/" + payment_id, values)

        if resp['status'] == 200:
            return resp['response']
