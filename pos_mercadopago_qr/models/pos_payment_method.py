# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pos_mp_qr_config_id = fields.Many2one('mp.credential', string='MP Credentials', help='The configuration of MP used for this journal')
    mp_qr_test_mode = fields.Boolean(help='Run transactions in the test environment.')

    def _get_payment_terminal_selection(self):
        return super(PoSPaymentMethod, self)._get_payment_terminal_selection() + [('mp_qr', 'MP QR')]

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super(PoSPaymentMethod, self)._onchange_use_payment_terminal()
        if self.use_payment_terminal != 'mp_qr':
            self.pos_mp_qr_config_id = False

