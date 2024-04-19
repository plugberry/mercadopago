# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class MPLog(models.Model):
    _name = 'mp.log'
    _rec_name = 'config_id'

    config_id = fields.Many2one('pos.config', string="Punto de venta")
    action = fields.Selection(
        [
            ('create_order', 'Crear orden'),
            ('remove_order', 'Eliminar orden'),
            ('get_order', 'Obtener orden'),
            ('refund_order', 'Devolver orden')
        ],
        string='Action'
    )
    header = fields.Char(string="Header")
    endpoint = fields.Char(string="Endpoint")
    status_code = fields.Char(string="Status code")
    request = fields.Text(string="Request")
    response = fields.Text(string="Response")

    def create_logs(self, config_id, action, headers, endpoint, status_code, payload, response):
        self.env['mp.log'].create({
            'config_id': config_id.id,
            'action': action,
            'header': headers,
            'endpoint': endpoint,
            'status_code': status_code,
            'request': payload,
            'response': response,
        })
        self.env.cr.commit()

