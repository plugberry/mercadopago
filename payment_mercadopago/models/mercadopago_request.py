import logging

from odoo import _
from odoo.exceptions import UserError
from werkzeug import urls
import pprint
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
        request_data = {"site_id":"MLA"}
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

    def payment(self, tx, token=None, form_data={}, cvv=True):
        """
        MercadoPago payment
        """
        if token:
            payment_token = tx.mercadopago_tmp_token if cvv and tx.mercadopago_tmp_token else self.get_card_token(token.card_token)
        elif 'mercadopago_token' in form_data:
            payment_token = form_data['mercadopago_token']

        capture, validation_capture_method = self.validation_capture_method(tx, form_data, token) 

        values = {
            "token": payment_token,
            "installments": 1 if token else form_data['installments'],
            "transaction_amount": tx.amount,
            "description": "Odoo ~ MercadoPago payment",
            "payment_method_id": token.acquirer_ref if token else form_data['mercadopago_payment_method'],
            "binary_mode": True,
            "external_reference": tx.reference,
            "payer": {
                "type": "customer",
                "id": token.customer_id if token else None,
                "email": token.email if token else form_data['email'],
                "first_name": tx.partner_name,
            },
            "additional_info": {
                "items": [{
                    "id": tx.acquirer_id.mercadopago_item_id,
                    "title": tx.acquirer_id.mercadopago_item_title,
                    "description": tx.acquirer_id.mercadopago_item_description,
                    "category_id": tx.acquirer_id.mercadopago_item_category or None,    
                    "quantity": 1,
                    "unit_price": tx.amount,
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
            "capture": capture,
        }
        if  hasattr(tx.partner_id, 'l10n_latam_identification_type_id'):
            values['payer']['identification'] = {
                    "number": tx.partner_id.vat,
                    "type": tx.partner_id.l10n_latam_identification_type_id.name,
            }

        if form_data.get("issuer"):
            values.update(issuer_id=form_data['issuer'])

        _logger.info("Payment values:\n%s", pprint.pformat(values))

        resp = self.mp.payment().create(values)
        resp = self.check_response(resp)
        if resp.get('err_code'):
            raise UserError(_("MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))
        else:
            if validation_capture_method == 'refund_payment':
                _logger.info(_('Refund validation payment id: %s ' % resp['id']))
                self.payment_refund(resp['id'])
            return resp

    def payment_refund(self, payment_id, amount = 0):
        """
        MercadoPago refund payment
        """
        if amount:
            values = {
                "amount": amount
            }
            resp = self.mp.refund().create(payment_id, values)
        else:
            resp = self.mp.refund().create(payment_id)

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
    
    def validation_capture_method(self,tx, form_data, token):
        """
        Validation capture method
            If transaction type is a validation, 
            Return a strategy to no capture the payment or refund it after validation.
            Return two values
             - Capture: if the transaction should be captured
             - Method: If a refund should be made.    
        """
        if tx.operation != 'validation':
            return True , None
        
        payment_method_id = token.acquirer_ref if token else form_data['mercadopago_payment_method']
        if self.payment_can_deferred_capture(payment_method_id):
            return False , 'deferred_capture'
        else:
            return True , 'refund_payment'
