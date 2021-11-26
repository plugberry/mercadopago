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

    def _handle_deactivation_request(self):
        """ Override of payment to request Authorize.Net to delete the token.

        Note: self.ensure_one()

        :return: None
        """
        return super()._handle_deactivation_request()

        # TODO: Borramos la tarjeta de MercadoPago cuando se archiva un token??
        # if self.provider != 'mercadopago':
        #     return
        # authorize_API = AuthorizeAPI(self.acquirer_id)
        # res_content = authorize_API.delete_customer_profile(self.authorize_profile)
        # _logger.info("delete_customer_profile request response:\n%s", pprint.pformat(res_content))

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Auth.net tokens cannot be restored.

        Note: self.ensure_one()

        :return: None
        """
        return super()._handle_reactivation_request()
        # if self.provider != 'authorize':
        #     return

        # raise UserError(_("Saved payment methods cannot be restored once they have been deleted."))

