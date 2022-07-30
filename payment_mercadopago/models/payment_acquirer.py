from locale import currency
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse

import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController
import pprint

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('mercadopago', 'MercadoPago')], ondelete={'mercadopago': 'set default'})
    mercadopago_publishable_key = fields.Char('MercadoPago Public Key', required_if_provider='mercadopago')
    mercadopago_access_token = fields.Char('MercadoPago Access Token', required_if_provider='mercadopago')
    is_validation = fields.Boolean()

    # MercadoPago general item fields
    mercadopago_item_id = fields.Char('Item ID')
    mercadopago_item_title = fields.Char('Item Title')
    mercadopago_item_description = fields.Char('Item Description')
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
    )

    @api.onchange('provider')
    def _onchange_provider(self):
        if self.provider == 'mercadopago':
            self.inline_form_view_id = self.env.ref('payment_mercadopago.inline_form').id

    def action_create_mercadopago_test_user(self):
        self.ensure_one()
        mercadopago_API = MercadoPagoAPI(self)
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
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist MercadoPago acquirers when the currency is not ARS. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        # TODO: Deberíamos forzar la moneda a ARS ??
        # currency = self.env['res.currency'].browse(currency_id).exists()
        # if currency and currency.name != 'ARS':
        #     acquirers = acquirers.filtered(lambda a: a.provider != 'mercadopago')

        return acquirers

    def _should_build_inline_form(self, is_validation=False):
        # if self.provider != 'mercadopago':
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
        if self.provider != 'mercadopago':
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
        if self.provider != 'mercadopago':
            return res

        # TODO: Deberíamos forzar la moneda a ARS ??
        return res

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'mercadopago':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mercadopago.payment_method_mercadopago').id
