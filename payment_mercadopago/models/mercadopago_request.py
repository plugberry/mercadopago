# -*- coding: utf-8 -*-
import logging

from odoo import _
from odoo.exceptions import UserError
from werkzeug import urls
from babel.dates import format_datetime
import requests

MP_URL = "https://api.mercadopago.com/"


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
        self.mercadopago_access_token = acquirer.mercadopago_access_token

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

    def check_api_response(self, resp):
        resp_json = resp.json()
        if resp.ok:
            return resp_json
        elif resp_json.get('cause'):
            return {
                'err_code': resp_json['cause'][0].get('code'),
                'err_msg': resp_json['cause'][0].get('description')
            }
        elif resp_json.get('error'):
            return {
                'err_code': resp_json.get('status', 0),
                'err_msg': resp_json.get('error')
            }
        else:
            return {
                'err_code': 500,
                'err_msg': "Server Error"
            }

    def unlink_card_token(self, customer_id, card_id):
        api_url = MP_URL + "v1/customers/%s/cards/%s" % (customer_id, card_id)
        headers = {"Authorization": "Bearer %s" % self.mercadopago_access_token}
        response = requests.delete(api_url, headers=headers)

    #create Test User
    def create_test_user(self):
        api_url = MP_URL + "users/test_user"
        headers = {"Authorization": "Bearer %s" % self.mercadopago_access_token}
        request_data = {"site_id": "MLA"}
        response = requests.post(api_url, headers=headers, json=request_data)
        resp = self.check_api_response(response)

        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

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
    def payment(self, tx, amount, capture=True, cvv_token=None):
        """
        MercadoPago payment
        """
        capture, validation_capture_method = self.validation_capture_method(tx)
        partner_email = tx.partner_id.email or tx.payment_token_id.partner_id.email
        values = {
            "token": cvv_token or self.get_card_token(tx.payment_token_id.token),
            "installments": tx.payment_token_id.installments,
            "transaction_amount": amount,
            "description": _("Odoo ~ MercadoPago payment"),
            "payment_method_id": tx.payment_token_id.acquirer_ref,
            "binary_mode": True if tx.type != 'validation' else False,
            "external_reference": tx.reference,
            "payer": {
                "type": "customer",
                "id": tx.payment_token_id.customer_id if tx.payment_token_id and tx.payment_token_id.customer_id else None,
                "email": partner_email,
                "first_name": tx.partner_name,
            },
            "additional_info": {
                "items": [{
                    "id": '001',
                    "title": _('Venta de ecommerce'),
                    "description": _('Venta de ecommerce'),
                    "category_id": 'others',
                    "quantity": 1,
                    "unit_price": amount,
                }],
                "payer": {
                    "first_name": tx.partner_name,
                    "phone": {
                        "number": tx.partner_phone
                    },
                    "address": {
                        "zip_code": tx.partner_zip,
                        "street_name": tx.partner_address,
                    },
                    "registration_date": format_datetime(tx.partner_id.create_date),
                },
            },
            "notification_url": urls.url_join(tx.acquirer_id.get_base_url(), '/payment/mercadopago/notify/%s?source_news=webhooks' % tx.acquirer_id.id),
            "capture": capture
        }

        if tx.payment_token_id.issuer:
            values.update(issuer_id=tx.payment_token_id.issuer)

        if hasattr(tx.partner_id, 'l10n_latam_identification_type_id'):
            values['payer']['identification'] = {
                "number": tx.partner_id.vat,
                "type": tx.partner_id.l10n_latam_identification_type_id.name,
            }

        if self.sandbox:
            _logger.info('values:\n%s' % values)

        resp = self.mp.payment().create(values)
        resp = self.check_response(resp)
        if resp.get('err_code'):
            _logger.info('send values:\n%s' % values)
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            if validation_capture_method == 'refund_payment' and resp.get('status') in ['approved'] :
                _logger.info(_('try Refund validation payment id: %s ' % resp['id']))
                # Reevaluar esto
                self.payment_refund(int(resp['id']))
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

    def payment_refund(self, payment_id, amount=0):
        """
        MercadoPago refund payment
        """
        if amount:
            values = {
                "amount": amount
            }
            return self.mp.refund().create(payment_id, values)
        else:
            return self.mp.refund().create(payment_id)

    def ensure_payment_refund(self, payment_id, amount=0):
        resp = self.payment_refund(payment_id, amount)
        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            return resp

    def payment_can_deferred_capture(self, payment_method_id):

        resp = self.mp.payment_methods().list_all()
        resp = self.check_response(resp)
        if type(resp) is dict and resp.get('err_code'):
            _logger.error(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
            return False
        payment = [d for d in resp if d['id'] == payment_method_id and d['status' ]=='active']
        if len(payment):
            return payment[0]['deferred_capture'] == 'supported'
        return False

    def validation_capture_method(self, tx):
        """
        Validation capture method
            If transaction type is a validation,
            Return a strategy to no capture the payment or  refund it after validation.
            Return two values
             - Capture: if the transaction should be captured
             - Method: If a refund should be made.
        """
        if tx.type != 'validation':
            return True, None
        elif tx.acquirer_id.mercadopago_capture_method == 'refund_payment':
            return True, 'refund_payment'

        payment_method_id = tx.payment_token_id.acquirer_ref
        if self.payment_can_deferred_capture(payment_method_id):
            return False, 'deferred_capture'
        else:
            return True, 'refund_payment'
