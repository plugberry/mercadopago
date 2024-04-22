# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class MPCredential(models.Model):
    _inherit = 'mp.credential'

    payment_type = fields.Selection(selection_add=[("mp_qr", "MP QR")])
