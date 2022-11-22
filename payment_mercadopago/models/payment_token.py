import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    email = fields.Char('Email', readonly=True)
    customer_id = fields.Char('MercadoPago Customer', readonly=True)
    issuer = fields.Char('Issuer', readonly=True)
    card_token = fields.Char('Card Token', readonly=True)
    bin = fields.Char('bin')

    def unlink(self):
        for token in self:
            if token.provider_id.code == 'mercadopago':
                mercado_pago = token.provider_id._get_mercadopago_request()
                mercado_pago.unlink_card_token(token.customer_id, token.card_token)

        return super().unlink()

    def _handle_deactivation_request(self):
        """ Override of payment to request Authorize.Net to delete the token.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_id.code == 'mercadopago':
            mercado_pago = self.provider_id._get_mercadopago_request()
            mercado_pago.unlink_card_token(self.customer_id, self.card_token)

        return super()._handle_deactivation_request()

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Auth.net tokens cannot be restored.

        Note: self.ensure_one()

        :return: None
        """
        if self.provider_id.code == 'mercadopago':
            raise UserError(_('You cannot reactive a Mercadopago token.'))

        return super()._handle_reactivation_request()

    def mercadopago_fix_token_bin(self):
        for token in self:

            mercadopago_API = token.provider_id._get_mercadopago_request()
            if token.customer_id:
                customer_id = token.customer_id
            else:
                customer_id = mercadopago_API.get_customer_profile(token.partner_id.email)
            token.bin = mercadopago_API.token_get_info(customer_id, token.card_token)['first_six_digits']
