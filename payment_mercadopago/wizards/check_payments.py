from odoo import fields, models
import logging
from odoo.addons.payment_mercadopago.models.mercadopago_request import MercadoPagoAPI
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PaymentMercadopagoCheckPayment(models.TransientModel):
    _name = "payment.mercadopago.check_payment"
    _description = "Mercadopago check payments"

    acquirer_id = fields.Many2one('payment.acquirer', domain="[('provider', '=', 'mercadopago')]", required=True)
    date_form = fields.Date(required=True, default = lambda self: fields.Date.today())
    date_to = fields.Date(required=True, default = lambda self: fields.Date.today())
    line_ids = fields.One2many('payment.mercadopago.check_payment.line', 'check_id', string='lines')
    confirmed = fields.Boolean(default=True)
    no_match = fields.Boolean()

    def check_status(self, mp_status, odoo_state):
        states = {
            'pending': 'pending',
            'approved': 'done',
            'authorized': 'authorized',
            'in_process': 'pending',
            'in_mediation': 'pending',
            'rejected': 'cancel',
            'cancelled': 'cancel',
            'refunded': 'done',
            'charged_back': 'done'
        }
        custom_state = states.get(mp_status)
        return odoo_state == custom_state

    def action_search_payments(self):
        MP = MercadoPagoAPI(self.acquirer_id)
        lines = []
        self.line_ids = False
        payments = MP.mp.payment().search(filters={'begin_date':str(self.date_form) + "T00:00:00.000Z", 'end_date':str(self.date_to) + "T23:59:59.000Z", 'limit':1})
        offset = 0
        total =  payments['response']['paging']['total']
        while offset <= total:
            filters={'begin_date':str(self.date_form) + "T00:00:00.000Z", 'end_date':str(self.date_to) + "T23:59:59.000Z", 'limit':100, 'offset':offset}
            _logger.info("Search in MP %s" % filters)
            payments = MP.mp.payment().search(filters=filters)
            offset += 100
            external_reference = [payment['external_reference'] for payment in payments['response']['results']]
            tx_ids = self.env['payment.transaction'].search([('reference', 'in', external_reference)])
            if 'results' in payments['response']:
                for payment in payments['response']['results']:
                    if not self.confirmed or payment.get('status') in ['refunded','approved','authorized','charged_back']:
                        transaction_id = tx_ids.filtered(lambda t: t.reference == payment['external_reference'])                    
                        if transaction_id and self.no_match and self.check_status(payment.get('status'), transaction_id.state):
                            continue
                        lines.append((0, 0, {
                            'mp_id': payment.get('id'),
                            'mp_amount': payment.get('transaction_amount'),
                            'mp_state': payment.get('status'),
                            'mp_external_reference':payment.get('external_reference'),
                            'mp_partner':payment.get('external_reference'),
                            'transaction_id': transaction_id.id
                        }))
        self.line_ids = lines
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'payment.mercadopago.check_payment',
                'res_id': self.id,
                'target': 'new',
                'views': [(self.env.ref('payment_mercadopago.check_payments_view_form').id, 'form')],
            }


class PaymentMercadopagoCheckPaymentLine(models.TransientModel):
    _name = "payment.mercadopago.check_payment.line"
    _description = "Mercadopago check payments"

    check_id = fields.Many2one('payment.mercadopago.check_payment')
    transaction_id = fields.Many2one('payment.transaction')
    transaction_state = fields.Selection('State', related='transaction_id.state')
    mp_amount = fields.Float()
    mp_id = fields.Char()
    mp_state = fields.Char()
    mp_external_reference = fields.Char()
    mp_partner = fields.Char()

    def get_tx_info_from_mercadopago(self):
        txt = []
        for rec in self:
            if rec.check_id.acquirer_id.provider != 'mercadopago':
                continue
            MP = MercadoPagoAPI(rec.check_id.acquirer_id)

            payments = MP.mp.payment().search(filters = {'external_reference': rec.mp_external_reference})
            for payment in payments['response']['results']:
                txt += ['---------------------------']
                txt += ["STATUS: %s" % payment['status']]
                txt += ["AMOUNT: %s" % payment['transaction_amount']]
                txt += ["description: %s" % payment['description']]
                txt += ['---------------------------']
                txt += ['%s: %s' % (x, payment[x]) for x in payment]
                txt += ['---------------------------']
                try:
                    rec._mercadopago_s2s_validate_tree(payment)
                except:
                    _logger.error('cant validate_tree')

        raise UserError("%s" % ' \n'.join(txt))
