# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    sale_point_id = fields.Many2one('mp.store.box.line', string='Punto de venta MP')

    def _compute_current_session(self):
        res = super(PosConfig, self)._compute_current_session()
        for pos_config in self:
            sale_point_id = self.env["mp.store.box.line"].sudo().search([("config_id", "=", pos_config.id)], limit=1)
            pos_config.sale_point_id = sale_point_id.id
        return res
