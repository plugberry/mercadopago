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
    _return_url = '/payment/mercadopago/return/'
    _cancel_url = '/payment/mercadopago/cancel/'

    @http.route([
        '/payment/mercadopago/return/',
        '/payment/mercadopago/cancel/',
    ], type='http', auth='public', csrf=False)
    def mercadopago_form_feedback(self, **post):
        import pdb; pdb.set_trace()
        _logger.info('MercadoPago: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'mercadopago')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Authorize.Net is expecting a response to the POST sent by their server.
        # This response is in the form of a URL that Authorize.Net will pass on to the
        # client's browser to redirect them to the desired location need javascript.
        return request.render('payment_mercadopago.payment_mercadopago_redirect', {
            'return_url': urls.url_join(base_url, "/payment/process")
        })

    @http.route(['/payment/mercadopago/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def mercadopago_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        import pdb; pdb.set_trace()
        token = False
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
            token = acquirer.s2s_process(kwargs)
        except:
            raise UserError(_("Error: mercadopago_s2s_create_json_3ds"))
        # except ValidationError as e:
        #     message = e.args[0]
        #     if isinstance(message, dict) and 'missing_fields' in message:
        #         if request.env.user._is_public():
        #             message = _("Please sign in to complete the payment.")
        #             # update message if portal mode = b2b
        #             if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
        #                 message += _(" If you don't have any account, ask your salesperson to grant you a portal access. ")
        #         else:
        #             msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
        #             message = msg + ', '.join(message['missing_fields']) + '. '
        #             message += _("Please complete your profile. ")

        #     return {
        #         'error': message
        #     }
        # except UserError as e:
        #     return {
        #         'error': e.name,
        #     }
        if not token:
            res = {
                'result': False,
            }
            # return res
            raise UserError(_("Error: mercadopago_s2s_create_json_3ds no token"))
        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': True,
        }
        return res

    @http.route(['/payment/mercadopago/s2s/create'], type='http', auth='public')
    def mercadopago_s2s_create(self, **post):
        import pdb; pdb.set_trace()
        acquirer_id = 13 #int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        acquirer.s2s_process(post)
        return utils.redirect("/payment/process")

