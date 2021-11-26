from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse
import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('mercadopago', 'MercadoPago')], ondelete={'mercadopago': 'set default'})
    mercadopago_publishable_key = fields.Char('MercadoPago Public Key', required_if_provider='mercadopago')
    mercadopago_access_token = fields.Char('MercadoPago Access Token', required_if_provider='mercadopago')
    is_validation = fields.Boolean()

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist MercadoPago acquirers when the currency is not ARS. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        # TODO: Deberíamos forzar la moneda a ARS ??
        # currency = self.env['res.currency'].browse(currency_id).exists()
        # if currency and currency.name != 'ARS':
        #     acquirers = acquirers.filtered(lambda a: a.provider != 'mercadopago')

        return acquirers

    def _should_build_inline_form(self, is_validation=False):
        # if self.provider != 'mercadopago':
        #     return super()._should_build_inline_form(self, is_validation=is_validation)

        # TODO: modify for redirect integration
        self.is_validation = is_validation
        return True

    def _get_validation_amount(self):
        """ Override of payment to return the amount for MercadoPago validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.provider != 'mercadopago':
            return res

        # TODO: definir un monto
        return 92.5

    def _get_validation_currency(self):
        """ Override of payment to return the currency for MercadoPago validation operations.

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        res = super()._get_validation_currency()
        if self.provider != 'mercadopago':
            return res

        # TODO: Deberíamos forzar la moneda a ARS ??
        return res

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'mercadopago':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mercadopago.payment_method_mercadopago').id
