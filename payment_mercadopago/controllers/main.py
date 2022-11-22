##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
import pprint
import json
from odoo import http, _
from odoo.http import request, Response
from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import ValidationError
from ..models.mercadopago_request import MercadoPagoAPI

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    _notify_url = '/payment/mercadopago/notify?source_news=webhooks'

    @http.route('/payment/mercadopago/get_provider_info', type='json', auth='public')
    def mercadopago_get_provider_info(self, rec_id, flow):
        """ Return public information on the provider.

        :param int rec_id: The payment option handling the transaction, as a `payment.provider` or `payment.token` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        provider_ref = False
        bin = False

        if flow == "token":
            token_sudo = request.env['payment.token'].browse(rec_id).sudo()
            provider_sudo = token_sudo.provider_id.sudo()
            provider_ref = token_sudo.provider_ref
            bin = token_sudo.bin
            # Esto lo agrego porque SDK V2 requiere el bin para calcular las coutas 
            if not bin:
                token_sudo.mercadopago_fix_token_bin()
                bin = token_sudo.bin
        else:
            provider_sudo = request.env['payment.provider'].sudo().browse(rec_id).exists()
        return {
            'publishable_key': provider_sudo.mercadopago_publishable_key,
            'bin': bin,
            'provider_ref': provider_ref,
        }

    @http.route('/payment/mercadopago/payment', type='json', auth='public')
    def mercadopago_payment(self, reference, partner_id, access_token, **kwargs):
        """ Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param dict mercadopago_token: Token returned by MercadoPago
        :return: None
        """

        # Check that the transaction details have not been altered
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError("MercadoPago: " + _("Received tampered payment request data."))

        # Make the payment request to MercadoPago
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        response_content = tx_sudo._mercadopago_create_transaction_request(kwargs)

        # Handle the payment request response
        _logger.info("make payment response:\n%s", pprint.pformat(response_content))
        feedback_data = {'reference': tx_sudo.reference, 'response': response_content}
        request.env['payment.transaction'].sudo()._get_tx_from_notification_data('mercadopago', feedback_data)

    @http.route('/payment/mercadopago/token', type='json', auth='user')
    def mercadopago_get_token_info(self, token_id):
        """ Return public information on the acquirer.

        :param int token_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :return: Information on the acquirer, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        token = request.env['payment.token'].browse(token_id).exists()
        return {
            'card_token': token.card_token,
        }

    @http.route([
        '/payment/mercadopago/notify',
        '/payment/mercadopago/notify/<int:aquirer_id>'
        ], type='json', auth='none')
    def mercadopago_notification(self, aquirer_id=False):
        """ Process the data sent by MercadoPago to the webhook based on the event code.

        :return: Status 200 to acknowledge the notification
        :rtype: Response
        """
        data = json.loads(request.httprequest.data)
        _logger.debug("MercadoPago notification: \n%s", pprint.pformat(data))

        if data['type'] == 'payment':
            try:
                # Payment ID
                payment_id = data['data']['id']

                # Get payment data from MercadoPago
                leaf = [('code', '=', 'mercadopago')]
                # For backward compatibility, add the aquirer_id separately.
                if aquirer_id:
                    leaf += [('id', '=', int(aquirer_id))]
                acquirer = request.env["payment.acquirer"].sudo().search(leaf, limit=1)

                mercadopago_API = MercadoPagoAPI(acquirer)
                payment_data = mercadopago_API.get_payment(payment_id)

                # Update transaction state
                PaymentTransaction = request.env['payment.transaction']
                feedback_data = {'reference': payment_data['external_reference'], 'response': payment_data}
                PaymentTransaction.sudo()._handle_feedback_data('mercadopago', feedback_data)

            except Exception:  # Acknowledge the notification to avoid getting spammed
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")

        # Acknowledge the notification
        return Response('success', status=200)
