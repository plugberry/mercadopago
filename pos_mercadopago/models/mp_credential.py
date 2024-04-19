# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class MPCredential(models.Model):
    _name = 'mp.credential'
    _description = 'Point of Sale MP Configuration'

    name = fields.Char(string='Name', required=True)
    mp_url = fields.Char(string='Url', required=True)
    user_id = fields.Char(string='Usuario')
    mp_access_token = fields.Char(string='Access token')
    payment_type = fields.Selection([], string='Tipo')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
