##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
import pprint
import werkzeug
from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
from odoo.addons.payment_mercadopago.models.mercadopago_request import MercadoPagoAPI
from urllib import parse
# TODO: remove to use the current sdk
from ..static.sdkpython.mercadopago import mercadopago
_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    # MercadoPago redirect controller
    _success_url = '/payment/mercadopago/success/'
    _pending_url = '/payment/mercadopago/pending/'
    _failure_url = '/payment/mercadopago/failure/'
    _create_preference_url = '/payment/mercadopago/create_preference'

    @http.route(['/payment/mercadopago/create_preference'], type='http', auth="none", csrf=False)
    def mercadopago_create_preference(self, **post):
        # TODO podriamos pasar cada elemento por separado para no necesitar
        # el literal eval
        # mercadopago_data = safe_eval(post.get('mercadopago_data', {}))
        acquirer = request.env['payment.acquirer'].browse(safe_eval(post.get('acquirer_id'))).sudo()
        mercadopago_preference = safe_eval(post.get('mercadopago_preference'))

        if not acquirer:
            return werkzeug.utils.redirect("/")

        # TODO: Remove this with sdk 1.2.0
        if (not mercadopago_preference or not acquirer.mercadopago_secret_key or not acquirer.mercadopago_client_id):
            _logger.warning('Missing parameters!')
            return werkzeug.utils.redirect("/")

        # TODO: remove to use the current sdk
        MP = mercadopago.MP(acquirer.mercadopago_client_id, acquirer.mercadopago_secret_key)
        MP.sandbox_mode(True) if acquirer.state == "enabled" else MP.sandbox_mode(False)
        resp = MP.post("/checkout/preferences", mercadopago_preference)
        linkpay = resp['response']['init_point'] if acquirer.state == "enabled" else resp['response']['sandbox_init_point']
        # TODO: Uncomment to use the current sdk
        # MP = MercadoPagoAPI(acquirer)
        # linkpay = MP.create_preference(mercadopago_preference)
        return werkzeug.utils.redirect(linkpay)

    @http.route([
        '/payment/mercadopago/success',
        '/payment/mercadopago/pending',
        '/payment/mercadopago/failure'
    ], type='http', auth="none")
    def mercadopago_back_no_return(self, **post):
        """
        Odoo, si usas el boton de pago desde una sale order o email, no manda
        una return url, desde website si y la almacena en un valor que vuelve
        desde el agente de pago. Como no podemos mandar esta "return_url" para
        que vuelva, directamente usamos dos distintas y vovemos con una u otra
        """
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
        }
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

    @http.route(['/payment/mercadopago/notification'], type='json', methods=['POST'], auth='public')
    def mercadopago_s2s_notification(self, **kwargs):
        querys = parse.urlsplit(request.httprequest.url).query
        params = dict(parse.parse_qsl(querys))
        if (params and params.get('payment_type') == 'payment' and params.get('data.id')):
            acquirer = request.env["payment.acquirer"].search([('provider', '=', 'mercadopago')])
            payment_id = params['data.id']
            tx = request.env['payment.transaction'].sudo().search([('acquirer_reference', '=', payment_id)])
            MP = MercadoPagoAPI(acquirer)
            tree = MP.get_payment(payment_id)
            return tx._mercadopago_s2s_validate_tree(tree)
        return False
