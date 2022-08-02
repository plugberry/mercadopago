# coding: utf-8
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse
import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    email = fields.Char('Email', readonly=True)
    issuer = fields.Char('Issuer', readonly=True)
    customer_id = fields.Char('MercadoPago Customer', readonly=True)    
    save_token = fields.Boolean('Save Token', default=True, readonly=True)
    token = fields.Char('Token', readonly=True)
    installments = fields.Integer('Installments', readonly=True)

    @api.model
    def mercadopago_create(self, values):
        if values.get('token') and values.get('payment_method_id'):

            #mercadopago_API = MercadoPagoAPI(self.acquirer_id)
            #customer_id = mercadopago_API.get_customer_profile(self.partner_id.email)

                # create the token
            return {
                    'name': "MercadoPago card token",
                    'acquirer_ref': values.get('payment_method_id'),
                    'email': values.get('email'),
                    #'customer_id': customer_id,
                    'issuer': values.get('issuer'),
                    'installments': int(values.get('installments', 1)),
                    'save_token': values.get('save_token') == "on",
                    'token': values.get('token'),
            }
        else:
            raise ValidationError(_('The Token creation in MercadoPago failed.'))

    def mercadopago_update(self, acquirer):
        # buscamos / creamos un customer
        MP = MercadoPagoAPI(acquirer)
        customer_id = MP.get_customer_profile(self.email)

        # TODO: si un cliente tokeniza dos veces la misma tarjeta, debemos buscarla en MercadoPago o crearla nuevamente?
        # card = None  # TODO: delete this
        # cards = MP.get_customer_cards(customer_id)
        # if card not in cards:
        card = MP.create_customer_card(customer_id, self.token)

        self.name = "%s: XXXX XXXX XXXX %s" % (self.acquirer_ref.capitalize(), card['last_four_digits'])
        self.installments = 1
        self.token = card['id']
        self.verified = True

    def hide_email(self, email):
        username = email.split("@")[0]
        return(email.replace(username, username[:3] + "***"))

    def unlink(self):
        for token in self:
            if token.acquirer_id.provider == 'mercadopago':
                mercado_pago = MercadoPagoAPI(token.acquirer_id)
                customer_id = mercado_pago.get_customer_profile(self.partner_id.email)

                mercado_pago.unlink_card_token(customer_id, token.token)

        return super().unlink()
