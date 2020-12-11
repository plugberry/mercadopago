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

    def _mercadopago_request(self, url, data):
        _logger.info('_mercadopago_request: Sending values to URL %s, values:\n%s', url, data)
        resp = self.mp.post(url, data)
        # TODO: mejorar checkeo de respuesta
        # resp.raise_for_status()
        # resp = json.loads(resp.content)
        # _logger.info("_mercadopago_request: Received response:\n%s", resp)
        # messages = resp.get('messages')
        # if messages and messages.get('resultCode') == 'Error':
        #     return {
        #         'err_code': messages.get('message')[0].get('code'),
        #         'err_msg': messages.get('message')[0].get('text')
        #     }

        return resp

    def get_customer_profile(self, partner):
        resp = self.mp.get('/v1/customers/search?%s' % partner.email)
        # TODO: improve check status
        if 'response' in resp and resp['response']['results']:
            return resp['response']['results'][0]['id']

    def create_customer_profile(self, partner):
        values = {
            'email': partner.email,
            # 'first_name': _partner_split_name(partner.name)[0],
            # 'last_name': _partner_split_name(partner.name)[1],
            # 'phone': {
            #     'area_code': '023',
            #     'number': '12345678'
            # },
            # 'identification': {
            #     'type': 'DNI',
            #     'number': '12345678'
            # },
            # 'address': {
            #     'zip_code': 'SG1 2AX',
            #     'street_name': 'Old Knebworth Ln'
            # },
            # 'description': 'Lorem Ipsum'
        }

        resp = self._mercadopago_request('/v1/customers', values)
        if resp and resp.get('err_code'):
            raise UserError(_(
                "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return {
            'id': resp.get('id'),
        }

    def get_customer_cards(self, customer_id):
        resp = self.mp.get('/v1/customers/%s/cards' % customer_id)
        # TODO: improve check status
        if 'response' in resp:
            return resp['response']

    def create_customer_card(self, customer_id, token):
        values = {
            "token": token
        }
        resp = self._mercadopago_request('/v1/customers/%s/cards' % customer_id, values)

        if resp and resp.get('err_code'):
            raise UserError(_(
                "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return resp['response']

    # Transaction management
    def payment(self, token, amount, reference, capture):
        """
        MercadoPago payment
        """
        values = {
                "token": token.acquirer_ref,
                "installments": 1,
                "transaction_amount": amount,
                "description": "Odoo ~ MercadoPago payment",
                "payment_method_id": token.mercadopago_payment_method,
                "payer": {
                    "email": token.partner_id.email,
                },
                "capture": capture
            }
        # if issuer_id:
        #         payment_data.update(issuer_id=issuer_id)

        # resp = self._mercadopago_request("/v1/payments", values)

        resp = {
            "id": 20359978,
            "date_created": "2019-07-10T10:47:58.000-04:00",
            "date_approved": "2019-07-10T10:47:58.000-04:00",
            "date_last_updated": "2019-07-10T10:47:58.000-04:00",
            "date_of_expiration": None,
            "money_release_date": "2019-07-24T10:47:58.000-04:00",
            "operation_type": "regular_payment",
            "issuer_id": "25",
            "payment_method_id": "visa",
            "payment_type_id": "credit_card",
            "status": "approved",
            "status_detail": "accredited",
            "currency_id": "[FAKER][CURRENCY][ACRONYM]",
            "description": "Point Mini a maquininha que dá o dinheiro de suas vendas na hora",
            "live_mode": False,
            "sponsor_id": None,
            "authorization_code": None,
            "money_release_schema": None,
            "taxes_amount": 0,
            "counter_currency": None,
            "shipping_amount": 0,
            "pos_id": None,
            "store_id": None,
            "collector_id": 448876418,
            "payer": {
                "first_name": "Test",
                "last_name": "Test",
                "email": "test_user_80507629@testuser.com",
                "identification": {
                    "number": "19119119100",
                    "type": "CPF"
                },
                "phone": {
                    "area_code": "011",
                    "number": "987654321",
                    "extension": ""
                    },
                    "type": "guest",
                    "entity_type": None,
                    "id": None
            },
            "metadata": {},
            "additional_info": {},
            "order": {},
            "external_reference": "MP0001",
            "transaction_amount": 58.8,
            "transaction_amount_refunded": 0,
            "coupon_amount": 0,
            "differential_pricing_id": None,
            "deduction_schema": None,
            "transaction_details": {
                "payment_method_reference_id": None,
                "net_received_amount": 56.16,
                "total_paid_amount": 58.8,
                "overpaid_amount": 0,
                "external_resource_url": None,
                "installment_amount": 58.8,
                "financial_institution": None,
                "payable_deferral_period": None,
                "acquirer_reference": None
            },
            "fee_details": [
                {
                    "type": "mercadopago_fee",
                    "amount": 2.64,
                    "fee_payer": "collector"
                }
            ],
            "captured": True,
            "binary_mode": False,
            "call_for_authorize_id": None,
            "statement_descriptor":"MercadoPago",
            "installments": 1,
            "card": {
                "id": None,
                "first_six_digits": "423564",
                "last_four_digits": "5682",
                "expiration_month": 6,
                "expiration_year": 2023,
                "date_created": "2019-07-10T10:47:58.000-04:00",
                "date_last_updated": "2019-07-10T10:47:58.000-04:00",
                "cardholder": {
                    "name": "APRO",
                    "identification": {
                        "number": "19119119100",
                        "type": "CPF"
                    }
                }
            },
            "notification_url": "https://www.suaurl.com/notificacoes/",
            "refunds": [],
            "processing_mode": "aggregator",
            "merchant_account_id": None,
            "acquirer": None,
            "merchant_number": None,
            "acquirer_reconciliation": []
        }
        return resp

    def payment_cancel(self, payment_id):
        """
        MercadoPago cancelation payment
        """
        values = {
                "status": "cancelled"
            }

        # access_token = self.MP.customer.get_access_token()
        # resp = self.MP.customer.get_rest_client().put("/v1/payments/" + payment_id + "?access_token=%s" % (access_token), values)

        resp = {
            "status": "cancelled",
            "status_detail": "by_collector",
            "captured": False,
        }
        return resp
