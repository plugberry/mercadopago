# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
_logger = logging.getLogger(__name__)


class MPStoreBoxLine(models.Model):
    _name = 'mp.store.box.line'
    _description = "Pos Terminal mp"

    config_id = fields.Many2one('pos.config', string="Punto de venta")
    name = fields.Char(string="Nombre de la caja", related='config_id.name', store=True)
    category = fields.Selection(
        [
            ('621102', 'Argentina')
        ],
        string='Código MCC', default='621102')
    external_id = fields.Char(string="Identificador único de la caja")
    store_box_id = fields.Many2one('mp.store.box', string="Store terminal")
    image_qr = fields.Char(string="Image QR")
    template_document_qr = fields.Char(string="Template document QR")
    template_image_qr = fields.Char(string="Template image QR")
    qr_code = fields.Char(string="QR code")
    fixed_amount = fields.Boolean(string="Fixed amount")
    box_id = fields.Char(string="Box ID")
    store_id = fields.Char(string="Store")
    external_store_id = fields.Char(string="External Store")
    user_id = fields.Char(string="User")
    active_box = fields.Boolean(string="Estado")

    def remove_point_box(self):
        credential_id = self.env['mp.credential'].search([('payment_type', '=', 'mp_qr')])
        if self.box_id:
            url = credential_id.mp_url + 'pos/' + self.box_id
            headers = {
                "Content-Type": "application/json",
                'Authorization': 'Bearer ' + '' + credential_id.mp_access_token,
            }
            try:
                response = requests.delete(url, headers=headers)
            except ConnectionError as error:
                raise ValidationError('Error comunicandose con la plataforma. Respuesta con error %s' % error)
            if response.status_code == 204:
                self.unlink()
            else:
                data_to_json = response.json()
                raise ValidationError('Error: %s' % data_to_json)
        else:
            self.unlink()

    def edit_point_box(self):
        credential_id = self.env['mp.credential'].search([('payment_type', '=', 'mp_qr')])
        url = credential_id.mp_url + 'pos/' + self.box_id
        headers = {
            "Content-Type": "application/json",
            'Authorization': 'Bearer ' + '' + credential_id.mp_access_token,
        }
        for rec in self:
            payload = {
                "category": int(rec.category),
                "fixed_amount": rec.fixed_amount,
                "name": rec.name,
                "store_id": int(rec.store_box_id.store_id.external_store_id)
            }
            try:
                response = requests.put(url, headers=headers, json=payload)
            except ConnectionError as error:
                raise ValidationError('Error comunicandose con la plataforma. Respuesta con error %s' % error)
            if response.status_code == 200:
                data_to_json = response.json()
                rec.write({'image_qr': data_to_json['qr']['image'],
                           'template_document_qr': data_to_json['qr']['template_document'],
                           'template_image_qr': data_to_json['qr']['template_image'],
                           'qr_code': data_to_json['qr_code'],
                           'box_id': data_to_json['id'],
                           'active_box': True
                           })
            else:
                data_to_json = response.json()
                raise ValidationError('Error: %s' % data_to_json)


class MPStoreBox(models.Model):
    _name = 'mp.store.box'

    name = fields.Char(string="Punto de venta ID")
    store_id = fields.Many2one('mp.store', string="Store")
    external_store_id = fields.Char(string="Identificador del store", related='store_id.external_store_id')
    box_line_ids = fields.One2many(
        "mp.store.box.line",
        "store_box_id",
        string="Terminal Line",
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('publish', 'Publicado')
        ],
        string='Estado', default='draft'
    )

    def publish_box(self):
        credential_id = self.env['mp.credential'].search([('payment_type', '=', 'mp_qr')])
        url = credential_id.mp_url + 'pos'
        headers = {
            "Content-Type": "application/json",
            'Authorization': 'Bearer ' + '' + credential_id.mp_access_token,
        }
        for rec in self:
            for box in rec.box_line_ids.filtered(lambda x: not x.active_box):
                payload = {
                      "category": int(box.category),
                      "external_id": rec.store_id.external_id + '' + 'POS' + str(box.config_id.id) + str(box.id),
                      "external_store_id": rec.store_id.external_id,
                      "fixed_amount": box.fixed_amount,
                      "name": box.name,
                      "store_id": int(rec.store_id.external_store_id)
                }
                try:
                    response = requests.post(url, headers=headers, json=payload)
                except ConnectionError as error:
                    raise ValidationError('Error comunicandose con la plataforma. Respuesta con error %s' % error)
                if response.status_code == 201:
                    data_to_json = response.json()
                    box.write({'image_qr': data_to_json['qr']['image'],
                               'template_document_qr': data_to_json['qr']['template_document'],
                               'template_image_qr': data_to_json['qr']['template_image'],
                               'qr_code': data_to_json['qr_code'],
                               'box_id': data_to_json['id'],
                               'active_box': True,
                               'external_id': data_to_json['external_id'],
                               'store_id': data_to_json['store_id'],
                               'user_id': data_to_json['user_id'],
                               'external_store_id': data_to_json['external_store_id']})
                else:
                    data_to_json = response.json()
                    raise ValidationError('Error: %s' % data_to_json)
            box_active = len(rec.box_line_ids.filtered(lambda x: x.active_box))
            box = len(rec.box_line_ids)
            if box_active == box:
                rec.write({'state': 'publish'})

    def to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})