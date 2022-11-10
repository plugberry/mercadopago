##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
import pprint
<<<<<<< HEAD
||||||| parent of 0d2d3c6... temp
import werkzeug
from odoo import http
from odoo.http import request, Response
from odoo.tools.safe_eval import safe_eval
from odoo.addons.payment_mercadopago.models.mercadopago_request import MercadoPagoAPI
from urllib import parse
=======
import werkzeug
from odoo import http
from odoo.http import request, Response
from odoo.tools.safe_eval import safe_eval
from odoo.addons.payment_mercadopago.models.mercadopago_request import MercadoPagoAPI
from odoo.exceptions import UserError
from urllib import parse
>>>>>>> 0d2d3c6... temp
import json
<<<<<<< HEAD
from odoo import http, _
from odoo.http import request, Response
from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import ValidationError
from ..models.mercadopago_request import MercadoPagoAPI

||||||| parent of 0d2d3c6... temp
=======

>>>>>>> 0d2d3c6... temp
_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    _notify_url = '/payment/mercadopago/notify?source_news=webhooks'

    @http.route('/payment/mercadopago/get_acquirer_info', type='json', auth='public')
    def mercadopago_get_acquirer_info(self, rec_id, flow):
        """ Return public information on the acquirer.

        :param int rec_id: The payment option handling the transaction, as a `payment.acquirer` or `payment.token` id
        :return: Information on the acquirer, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        if flow == "token":
            acquirer_sudo = request.env['payment.token'].browse(rec_id).acquirer_id.sudo()
        else:
            acquirer_sudo = request.env['payment.acquirer'].sudo().browse(rec_id).exists()
        return {
            'publishable_key': acquirer_sudo.mercadopago_publishable_key,
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
        request.env['payment.transaction'].sudo()._handle_feedback_data('mercadopago', feedback_data)

    @http.route('/payment/mercadopago/token', type='json', auth='public')
    def mercadopago_get_token_info(self, token_id):
        """ Return public information on the acquirer.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :return: Information on the acquirer, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
<<<<<<< HEAD
        token = request.env['payment.token'].sudo().browse(token_id).exists()
        return {
            'card_token': token.card_token,
||||||| parent of 0d2d3c6... temp
        _logger.info('Mercadopago: entering mecadopago_back with post data %s', pprint.pformat(post))
        request.env['payment.transaction'].sudo().form_feedback(post, 'mercadopago')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/mercadopago/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def mercadopago_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = False
        error = None

        try:
            token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        except Exception as e:
            error = str(e)

        if not token:
            res = {
                'result': False,
                'error': error,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
=======
        _logger.info('Mercadopago: entering mecadopago_back with post data %s', pprint.pformat(post))
        request.env['payment.transaction'].sudo().form_feedback(post, 'mercadopago')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/mercadopago/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def mercadopago_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            return_url = kwargs.get('return_url', '')
            if return_url.startswith('/my/subscription/'):

                return_url = return_url.split('/')
                res_id = int(return_url[-2])
                uuid = return_url[-1]
                subscription = request.env['sale.subscription'].sudo().browse(res_id).exists()
                if not subscription or not uuid or subscription.uuid != uuid:
                    res = {
                            'result': False,
                            'error': 'La suscripción es invalida',
                    }
                    return res

                kwargs = dict(kwargs, partner_id=subscription.partner_id.id)
            else:
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = False
        error = None

        try:
            token = request.env['payment.acquirer'].sudo().browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        except Exception as e:
            _logger.error(e)
            error = str(e)

        if not token:
            res = {
                'result': False,
                'error': error,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
>>>>>>> 0d2d3c6... temp
        }
<<<<<<< HEAD

    @http.route([
        '/payment/mercadopago/notify', 
        '/payment/mercadopago/notify/<int:aquirer_id>'
        ], type='json', auth='none')
    def mercadopago_notification(self, aquirer_id=False):
||||||| parent of 0d2d3c6... temp
        if verify_validity:
            token.validate()
            res['verified'] = token.verified

        return res

    @http.route(['/payment/mercadopago/s2s/otp'], type='json', auth='public')
    def mercadopago_s2s_otp(self, **kwargs):
        cvv_token = kwargs.get('token')
        # request.session.update(kwargs)
        request.session.update({'cvv_token': cvv_token})
        return {'result': True}

    @http.route(['/payment/mercadopago/notify',
                 '/payment/mercadopago/notify/<int:acquirer_id>'],
                type='json', auth='none')
    def mercadopago_notification(self,acquirer_id=False):
=======
        if verify_validity:
            tx = token.validate()
            _logger.info("TX a validar %s" % tx)
            if tx.state == 'error':
                # Si la operación dio error la elimino
                _logger.error("Se hace rollback de la transaccion %s por error %s " % (tx.id, tx.state_message))
                raise UserError(tx.state_message)
            res['verified'] = token.verified

        return res

    @http.route(['/payment/mercadopago/s2s/otp'], type='json', auth='public')
    def mercadopago_s2s_otp(self, **kwargs):
        cvv_token = kwargs.get('token')
        # request.session.update(kwargs)
        request.session.update({'cvv_token': cvv_token})
        return {'result': True}

    @http.route(['/payment/mercadopago/notify',
                 '/payment/mercadopago/notify/<int:acquirer_id>'],
                type='json', auth='public')
    def mercadopago_notification(self, acquirer_id=False):
>>>>>>> 0d2d3c6... temp
        """ Process the data sent by MercadoPago to the webhook based on the event code.

        :return: Status 200 to acknowledge the notification
        :rtype: Response
        """
        data = json.loads(request.httprequest.data)
        _logger.info("MercadoPago notification: \n%s", pprint.pformat(data))
        if data['type'] == 'payment':
            try:
                # Payment ID
                payment_id = data['data']['id']

                # Get payment data from MercadoPago
                leaf=[('provider', '=', 'mercadopago')]
                #For backward compatibility, add the aquirer_id separately.
                if aquirer_id:
                    leaf += [('id', '=', int(aquirer_id))]
                acquirer = request.env["payment.acquirer"].sudo().search(leaf, limit=1)
<<<<<<< HEAD

                mercadopago_API = MercadoPagoAPI(acquirer)
                payment_data = mercadopago_API.get_payment(payment_id)

                # Update transaction state
                PaymentTransaction = request.env['payment.transaction']
                feedback_data = {'reference': payment_data['external_reference'], 'response': payment_data}
                PaymentTransaction.sudo()._handle_feedback_data('mercadopago', feedback_data)
||||||| parent of 0d2d3c6... temp
                MP = MercadoPagoAPI(acquirer)
                tree = MP.get_payment(payment_id)
                tx = request.env['payment.transaction'].sudo().search(
                    [('acquirer_reference', '=', payment_id), 
                     ('acquirer_id', '=', acquirer.id)]
                )
                tx._mercadopago_s2s_validate_tree(tree)
=======
                MP = MercadoPagoAPI(acquirer)
                tree = MP.get_payment(payment_id)
                tx = request.env['payment.transaction'].sudo().search(
                    [('acquirer_reference', '=', payment_id),
                     ('acquirer_id', '=', acquirer.id)]
                )
                tx._mercadopago_s2s_validate_tree(tree)
>>>>>>> 0d2d3c6... temp

            except Exception:  # Acknowledge the notification to avoid getting spammed
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")

        # Acknowledge the notification
        return Response('success', status=200)
