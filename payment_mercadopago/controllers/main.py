##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import pprint
import logging
from werkzeug import urls, utils

from odoo import http, fields
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
try:
    from mercadopago import mercadopago
except ImportError:
    _logger.debug('Cannot import external_dependency mercadopago')


class MercadoPagoController(http.Controller):
    _notify_url = '/payment/mercadopago/notification?source_news=webhooks'

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
    def mercadopago_s2s_notification(self, payment_id=None, type=None, **kwargs):
        IrLogging = request.env['ir.logging']
        IrLogging.sudo().create({
                    'name': 'MercadoPago Notification!',
                    'type': 'client',
                    'dbname': 'Odoo13',
                    'level': 'DEBUG',
                    'message': kwargs,
                    'path': "/payment/mercadopago/notification",
                    'func': "mercadopago_s2s_notification",
                    'line': 1})
        return True
