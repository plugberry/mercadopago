##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

# import pprint
import logging

from odoo import http
from odoo.http import request
from odoo.addons.payment_mercadopago.models.mercadopago_request import MercadoPagoAPI
from urllib import parse

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

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
