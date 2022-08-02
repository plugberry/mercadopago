# coding: utf-8
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse
import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController

_logger = logging.getLogger(__name__)

class PaymentAcquirerMercadoPago(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('mercadopago', 'MercadoPago')])
    mercadopago_publishable_key = fields.Char('MercadoPago Public Key', required_if_provider='mercadopago')
    mercadopago_access_token = fields.Char('MercadoPago Access Token', required_if_provider='mercadopago')

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerMercadoPago, self)._get_feature_support()
        res['tokenize'].append('mercadopago')
        res['fees'].append('mercadopago')
        return res

    def mercadopago_compute_fees(self, amount, currency_id, country_id):
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = percentage / 100.0 * amount + fixed
        return fees

    def mercadopago_form_generate_values(self, values):
        self.ensure_one()
        tx_values = dict(values)
        base_url = self.get_base_url()

        success_url = MercadoPagoController._success_url
        failure_url = MercadoPagoController._failure_url
        pending_url = MercadoPagoController._pending_url
        return_url = tx_values.get('return_url')
        # si hay return_url se la pasamos codificada asi cuando vuelve
        # nos devuelve la misma
        if return_url:
            url_suffix = '{}{}'.format('?', werkzeug.urls.url_encode({'return_url': return_url}))
            success_url += url_suffix
            failure_url += url_suffix
            pending_url += url_suffix

        # TODO, implement, not implemented yet because mercadopago only
        # shows description of first line and we would need to send taxes too
        # sale_order = self.env['sale.order'].search(
        #     [('name', '=', tx_values["reference"])], limit=1)
        # if self.mercadopago_description == 'so_lines' and sale_order:
        #     items = [{
        #         "title": line.name,
        #         "quantity": line.product_uom_qty,
        #         "currency_id": (
        #             tx_values['currency'] and
        #             tx_values['currency'].name or ''),
        #         "unit_price": line.price_unit,
        #     } for line in sale_order.order_line]
        # else:
        items = [{
            "title": _("Order %s") % (tx_values["reference"]),
            "quantity": 1,
            "currency_id": (tx_values['currency'] and tx_values['currency'].name or ''),
            "unit_price": tx_values["amount"]
        }]

        if self.fees_active:
            items.append({
                "title": _('Recargo por Mercadopago'),
                "quantity": 1,
                "currency_id": (tx_values['currency'] and tx_values['currency'].name or ''),
                "unit_price": tx_values.pop('fees', 0.0)
            })

        preference = {
            "items": items,
            "payer": {
                "name": values["billing_partner_first_name"],
                "surname": values["billing_partner_last_name"],
                "email": values["partner_email"]
            },
            "back_urls": {
                "success": '%s' % urlparse.urljoin(base_url, success_url),
                "failure": '%s' % urlparse.urljoin(base_url, failure_url),
                "pending": '%s' % urlparse.urljoin(base_url, pending_url)
            },
            "auto_return": "approved",
            "external_reference": tx_values["reference"],
            "expires": False
        }
        tx_values.update({
            'acquirer_id': self.id,
            'mercadopago_preference': preference
        })
        return tx_values

    def mercadopago_get_form_action_url(self):
        self.ensure_one()
        return MercadoPagoController._create_preference_url

    @api.model
    def mercadopago_s2s_form_process(self, data):
        values = {
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id')),
            'token': data.get('token'),
            'payment_method_id': data.get('payment_method_id'),
            'email': data.get('email'),
            'issuer': data.get('issuer'),
            'installments': data.get('installments'),
            'save_token': data.get('save_token')
        }
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    def mercadopago_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["token", "payment_method_id"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return False if error else True
