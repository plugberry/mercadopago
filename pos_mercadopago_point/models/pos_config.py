# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_pos_mp_point = fields.Boolean(string="MP Point",
                                        help="The transactions are processed by MP. Set your MP credentials on the related payment method.")
