# -*- encoding: utf-8 -*-
#
# Module written to Odoo, Open Source Management Solution
#
# Copyright (c) 2019 Telematel - http://www.telematel.com/
# All Rights Reserved.
#
# Developer(s): Randy La Rosa Alvarez
#               (randi.larosa@telematel.com)
########################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
########################################################################
from odoo import models, fields, api, _


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    token_card = fields.Char(
        string="Token card",
        readonly=True)
    card_id = fields.Char(
        string="Card",
        readonly=True)
    installments = fields.Integer()
    acquirer_ref = fields.Char('Acquirer Ref.', required=False)
    issuer_id = fields.Integer()
    mercadopago = fields.Boolean()
    payment_method_id = fields.Char()

    def get_name_to_token_payment(self, card_name, partner_name):
        name_token = card_name + ' - ' + partner_name + _(' By MercadoPago')
        return name_token

    @api.model
    def mercadopago_create_payment_token(
            self,
            card_name,
            partner_id,
            issuer_id,
            installments,
            payment_method_id,
            token_card,
            payment_id,
            card_id=''
    ):
        tokens = self.sudo().search([('partner_id', '=', partner_id)],
                                    order='create_date')
        if len(tokens) >= 3:
            tokens[0].unlink()
        partner = self.env['res.partner'].sudo().browse(partner_id)
        token_name = self.get_name_to_token_payment(card_name, partner.name)
        try:
            payment_token = self.sudo().create(
                {
                    'name': token_name,
                    'partner_id': partner_id,
                    'acquirer_id': payment_id.id,
                    'token_card': token_card,
                    'verified': True,
                    'payment_method_id': payment_method_id,
                    'installments': installments,
                    'issuer_id': issuer_id,
                    'mercadopago': True,
                    'card_id': card_id
                }
            )
        except Exception as e:
            payment_token = False
        return payment_token

