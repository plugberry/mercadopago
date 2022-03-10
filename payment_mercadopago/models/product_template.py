from .mercadopago_request import MercadoPagoAPI
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    mercadopago_category_id = fields.Selection(
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
