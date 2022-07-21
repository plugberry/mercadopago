from .mercadopago_request import MercadoPagoAPI
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


    def unlink(self):
        for token in self:
            if token.acquirer_id.provider == 'mercadopago':
                mercado_pago = MercadoPagoAPI(token.acquirer_id)
                mercado_pago.unlink_card_token(token.customer_id, token.card_token)

        return super().unlink()

    def _handle_deactivation_request(self):
        """ Override of payment to request Authorize.Net to delete the token.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.acquirer_id.provider == 'mercadopago':
            mercado_pago = MercadoPagoAPI(self.acquirer_id)
            mercado_pago.unlink_card_token(self.customer_id, self.card_token)

        return super()._handle_deactivation_request()

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Auth.net tokens cannot be restored.

        Note: self.ensure_one()

        :return: None
        """
        if self.acquirer_id.provider == 'mercadopago':
            raise UserError(_('You cannot reactive a Mercadopago token.'))


        return super()._handle_reactivation_request()

