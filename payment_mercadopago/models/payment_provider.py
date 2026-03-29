from locale import currency
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse

import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController
import pprint
from payment_mercadopago import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mercadopago', 'MercadoPago')], ondelete={'mercadopago': 'set default'})

    mercadopago_publishable_key = fields.Char('MercadoPago Public Key')
    mercadopago_access_token = fields.Char('MercadoPago Access Token')
    mercadopago_test_publishable_key = fields.Char('MercadoPago test Public Key')
    mercadopago_test_access_token = fields.Char('MercadoPago test Access Token')
    is_validation = fields.Boolean()

    # MercadoPago general item fields
    mercadopago_item_id = fields.Char('Item ID', default='001')
    mercadopago_item_title = fields.Char('Item Title', default='Website sale')
    mercadopago_item_description = fields.Char('Item Description', default='Website sale item')
    mercadopago_item_category = fields.Selection(
        string='MercadoPago Category', help="The category",
        selection=[
            ('art', "Collectibles & Art"),
            ('baby', "Toys for Baby, Stroller, Stroller Accessories, Car Safety Seats"),
            ('coupons', "Coupons"),
            ('donations', "Donations"),
            ('computing', "Computers & Tablets"),
            ('cameras', "Cameras & Photography"),
            ('video_games', "Video Games & Consoles"),
            ('television', "LCD, LED, Smart TV, Plasmas, TVs"),
            ('car_electronics', "Car Audio, Car Alarm Systems & Security, Car DVRs, Car Video Players, Car PC"),
            ('electronics', "Audio & Surveillance, Video & GPS, Others"),
            ('automotive', "Parts & Accessories"),
            ('entertainment', "Music, Movies & Series, Books, Magazines & Comics, Board Games & Toys"),
            ('fashion', "Men's, Women's, Kids & baby, Handbags & Accessories, Health & Beauty, Shoes, Jewelry & Watches"),
            ('games', "Online Games & Credits"),
            ('home', "Home appliances. Home & Garden"),
            ('musical', "Instruments & Gear"),
            ('phones', "Cell Phones & Accessories"),
            ('services', "General services"),
            ('learnings', "Trainings, Conferences, Workshops"),
            ('tickets', "Tickets for Concerts, Sports, Arts, Theater, Family, Excursions tickets, Events & more"),
            ('travels', "Plane tickets, Hotel vouchers, Travel vouchers"),
            ('virtual_goods', "E-books, Music Files, Software, Digital Images, PDF Files and any item which can be electronically stored in a file, Mobile Recharge, DTH Recharge and any Online Recharge"),
            ('others', "Other categories"),
        ],
        default='others'
    )
    mercadopago_capture_method = fields.Selection([
        ('deferred_capture', 'Deferred capture is posible'),
        ('refund_payment', 'Always refund payment')
        ],
        string='Capture method',
        default='deferred_capture'
    )
    
    mercadopago_binary = fields.Boolean('Use binary mode', default=True)

    def _get_mercadopago_request(self):
        return MercadoPagoAPI(self)

    def _get_mercadopago_publishable_key(self):
        self.ensure_one()
        if self.state == 'test':
            return self.mercadopago_test_publishable_key
        elif self.state == 'enabled':
            return self.mercadopago_publishable_key

    def _get_mercadopago_access_token(self):
        self.ensure_one()
        if self.state == 'test':
            return self.mercadopago_test_access_token
        elif self.state == 'enabled':
            return self.mercadopago_access_token

    @api.onchange('code')
    def _onchange_code(self):
        if self.code == 'mercadopago':
            self.inline_form_view_id = self.env.ref('payment_mercadopago.inline_form').id

    def action_create_mercadopago_test_user(self):
        self.ensure_one()
        mercadopago_API = self._get_mercadopago_request()
        values = mercadopago_API.create_test_user()
        msg = _("Mercadopago test user id: {id},  nickname: {nickname}, password: {password}, status: {site_status}, email: {email} ").format(**values) 

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": msg,
                "type": "success",
                "sticky": True,
            },
        }


    @api.model
    def _get_supported_currencies(self):
        """ Override of payment to unlist MercadoPago providers when the currency is not ARS. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'mercadopago':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'mercadopago':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _should_build_inline_form(self, is_validation=False):
        # if self.code != 'mercadopago':
        #     return super()._should_build_inline_form(self, is_validation=is_validation)

        # TODO: modify for redirect integration
        self.is_validation = is_validation
        return True

    def _get_validation_amount(self):
        """ Override of payment to return the amount for MercadoPago validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'mercadopago':
            return res

        usd_currency_id = self.env.ref('base.USD')
        currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id
        amount = usd_currency_id._convert(1, currency_id, self.journal_id.company_id, fields.Date.today())
        return amount


    def _get_validation_currency(self):
        """ Override of payment to return the currency for MercadoPago validation operations.

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        res = super()._get_validation_currency()
        if self.code != 'mercadopago':
            return res

        # TODO: Deberíamos forzar la moneda a ARS ??
        return res

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mercadopago').update({
            'support_manual_capture': False,
            'support_refund': 'partial',
            'support_tokenization': True,
        })
