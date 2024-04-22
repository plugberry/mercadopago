# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
import requests
import json
import uuid
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    mp_point_payment_token = fields.Char(string='Payment token')

    def make_payment_mp_point(self, order):
        pos_session_id = self.env['pos.session'].search([('id', '=', order['pos_session_id'])])
        sale_point_id = pos_session_id.config_id.sale_point_id
        pos_payment_method_id = self.env['pos.payment.method'].search([('id', '=', order['payment_method_id'])])
        device_id = sale_point_id.terminal_id
        configuration_id = pos_payment_method_id.pos_mp_point_config_id
        access_token = configuration_id.mp_access_token or ''
        url = configuration_id.mp_url
        endpoint = url + '' + 'point/integration-api/devices/' + device_id + '/payment-intents'
        headers = {'Content-Type': 'application/json', 'x-test-scope': 'sandbox', 'Authorization': 'Bearer ' + '' + access_token}

        if isinstance(order['amount_total'], int):
            amount_total = order['amount_total']
            amount_total = str(amount_total).split(".")[0] + str(amount_total).split(".")[1] + '0' if len(str(amount_total).split(".")[1]) == 1 else str(amount_total).split(".")[0] + str(amount_total).split(".")[1]
            amount_total_str = amount_total
        else:
            amount_total = round(order['amount_total'], 3)
            amount_total_str = str(amount_total).split(".")[0] + str(amount_total).split(".")[1] + '0' if len(str(amount_total).split(".")[1]) == 1 else str(amount_total).split(".")[0] + str(amount_total).split(".")[1]
        payload = {
            "additional_info": {
                "external_reference": order['order_uid'],
                "print_on_terminal": False,
                "ticket_number": order['order_uid']
            },
            "amount": int(amount_total_str)
        }
        _logger.info('*************************Sending  request to MP POINT for sale******************************')
        _logger.info('********************Payload ************************************************* %s' % payload)
        response = requests.request("POST", endpoint, headers=headers, data=json.dumps(payload))
        status_code = response.status_code
        if response.status_code == 201:
            response = response.json()
            payment_id = order['order_uid']
            token_id = response['id']
            _logger.info('****************Payment data %s ****************' % payment_id)
            vals = {
                'status_code': 200,
                'payment_id': payment_id,
                'token_id': token_id
            }
        else:
            vals = {
                'status_code': response.status_code,
                'error': response.json()['message']
            }
        log = self.env['mp.log']
        log.create_logs(pos_session_id.config_id, 'create_order', headers, endpoint, status_code, payload, response)
        return vals

    def updating_order_point(self, order):
        pos_order_id = self.env['pos.order'].search([('access_token', '=', order['access_token_order'])])
        pos_order_id.write({'mp_point_payment_token': order['mp_point_payment_id']})
        return True

    def make_cancel_point(self, order):
        pos_session_id = self.env['pos.session'].search([('id', '=', order['pos_session_id'])])
        sale_point_id = pos_session_id.config_id.sale_point_id
        pos_payment_method_id = self.env['pos.payment.method'].search([('id', '=', order['payment_method_id'])])
        configuration_id = pos_payment_method_id.pos_mp_point_config_id
        device_id = sale_point_id.terminal_id
        access_token = configuration_id.mp_access_token or ''
        url = configuration_id.mp_url
        endpoint = url + '' + 'point/integration-api/devices/' + '' + device_id + '/payment-intents/' + order['token_point_ref_id']
        headers = {'Content-Type': 'application/json', 'x-test-scope': 'sandbox', 'Authorization': 'Bearer ' + '' + access_token}
        _logger.info('*************************Sending  request to MP for sale******************************')
        response = requests.request("DELETE", endpoint, headers=headers)
        if response.status_code == 200:
            _logger.info('**********************Payment info cancellations **************************')
            _logger.info(response)
        log = self.env['mp.log']
        log.create_logs(pos_session_id.config_id, 'remove_order', headers, endpoint, response.status_code, '', '')

    def get_payment_status_mp_point(self, order):
        vals = {}
        pos_session_id = self.env['pos.session'].search([('id', '=', order['pos_session_id'])])
        pos_payment_method_id = self.env['pos.payment.method'].search([('id', '=', order['payment_method_id'])])
        configuration_id = pos_payment_method_id.pos_mp_point_config_id
        access_token = configuration_id.mp_access_token or ''
        url = configuration_id.mp_url
        endpoint = url + '' + 'v1/payments/search?external_reference=' + '' + order['payment_point_ref_id']
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + '' + access_token}
        _logger.info('*************************Sending  request to MPQR for sale******************************')
        response = requests.request("GET", endpoint, headers=headers)
        status_code = response.status_code
        if status_code == 200:
            response = response.json()
            status = response['results'][-1]['status']
            vals = {
                'status_code': 200,
                'payment_status': status,
                'payment_id': response['results'][0]['id']
            }
        log = self.env['mp.log']
        log.create_logs(pos_session_id.config_id, 'get_order', headers, endpoint, status_code, '', response)
        return vals

    def make_refunds_mp_point(self, order):
        pos_order_id = self.env['pos.order'].search([('id', 'in', order['toRefundLines_ids'])])
        pos_payment_method_id = self.env['pos.payment.method'].search([('id', '=', order['payment_method_id'])])
        configuration_id = pos_payment_method_id.pos_mp_point_config_id
        access_token = configuration_id.mp_access_token or ''
        url = configuration_id.mp_url
        idempotency = str(uuid.uuid4())
        endpoint = url + '' + 'v1/payments/' + '' + pos_order_id[0].mp_point_payment_token + '/refunds'
        headers = {'Content-Type': 'application/json', 'X-Idempotency-Key': idempotency,  'Authorization': 'Bearer ' + '' + access_token}
        _logger.info('*************************Sending  request to MPQR for sale******************************')
        payload = {
            'amount': abs(order['amount_total'])
        }
        response = requests.request("POST", endpoint, headers=headers, data=json.dumps(payload))
        status_code = response.status_code
        if status_code == 201:
            response = response.json()
            payment_id = response
        else:
            response = response.json()
            vals = {
                'error': response['error'],
                'message': response['message']
            }
        log = self.env['mp.log']
        log.create_logs(pos_order_id.config_id, 'refund_order', headers, endpoint, status_code, payload, response)
        return vals









