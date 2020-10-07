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
        if acquirer.state == 'test':
            self.mp = mercadopago.MP('TEST-3834170027218729-082509-763e2577356637318da741a535bf25ec-628558216')
        else:
            self.mp = mercadopago.MP(acquirer.mercadopago_secret_key) # TODO: here would be the production token

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
        import pdb; pdb.set_trace()
        resp = self.mp.get('/v1/customers/search?%s' % partner.email)
        # TODO: improve check status
        if 'response' in resp and resp['response']['results']:
            return resp['response']['results'][0]['id']

    def create_customer_profile(self, partner):
        values = {
            'email': partner.email,
            'first_name': _partner_split_name(partner.name)[0],
            'last_name': _partner_split_name(partner.name)[1],
            'phone': {
                'area_code': '023',
                'number': '12345678'
            },
            'identification': {
                'type': 'DNI',
                'number': '12345678'
            },
            'address': {
                'zip_code': 'SG1 2AX',
                'street_name': 'Old Knebworth Ln'
            },
            'description': 'Lorem Ipsum'
        }

        resp = self._mercadopago_request('/v1/customers', values)
        if resp and resp.get('err_code'):
            raise UserError(_(
                "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return {
            'id': resp.get('id'),
        }

    def get_customer_cards(self, customer_id):
        import pdb; pdb.set_trace()
        resp = self.mp.get('/v1/customers/%s/cards' % customer_id)
        # TODO: improve check status
        if 'response' in resp:
            return resp['response']

    def create_customer_card(self, customer_id, token):
        values = {
            "token": token
        }
        import pdb; pdb.set_trace()
        resp = self._mercadopago_request('/v1/customers/%s/cards' % customer_id, values)

        # {'response': {'cause': [{'code': '140', 'description': 'invalid card owner'}],
        #       'error': 'bad_request',
        #       'message': 'invalid parameters ',
        #       'status': 400},
        #  'status': 400}

        if resp and resp.get('err_code'):
            raise UserError(_(
                "MercadoPago Error:\nCode: %s\nMessage: %s" % (resp.get('err_code'), resp.get('err_msg'))))

        return resp
