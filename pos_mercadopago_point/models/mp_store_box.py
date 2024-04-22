# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
_logger = logging.getLogger(__name__)


class MPStoreBoxLine(models.Model):
    _inherit = 'mp.store.box.line'

    terminal_id = fields.Char('Terminal')
    operating_mode = fields.Char('Modo de operación')


class MPStoreBox(models.Model):
    _inherit = 'mp.store.box'

    def get_terminal(self):
        credential_id = self.env['mp.credential'].search([('payment_type', '=', 'mp_point')])
        url = credential_id.mp_url + 'point/integration-api/devices'
        headers = {
            "Content-Type": "application/json",
            "x-test-scope": 'sandbox',
            'Authorization': 'Bearer ' + '' + credential_id.mp_access_token,
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response = response.json()
            for rec in self:
                for terminal in response['devices']:
                    if terminal['store_id'] == rec.external_store_id:
                        # pos = rec.box_line_ids.filtered(lambda x: x.box_id == terminal['pos_id'])
                        pos = rec.box_line_ids[0]
                        pos.write({'terminal_id': terminal['id'], 'operating_mode': terminal['operating_mode']})
