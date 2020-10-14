# coding: utf-8
from werkzeug import urls

from .mercadopago_request import MercadoPagoAPI
from mercadopago import mercadopago
import hashlib
import hmac
import logging
import time

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
# from odoo.addons.payment_mercadopago.controllers.sdk-python.mercadopago import
# from ..controllers.main import MercadoPagoController
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentAcquirerMercadoPago(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('mercadopago', 'MercadoPago')])
    # mercadopago_client_id = fields.Char('MercadoPago Client Id', required_if_provider='mercadopago')
    # mercadopago_secret_key = fields.Char('MercadoPago Secret Key', required_if_provider='mercadopago')
    mercadopago_public_key = fields.Char('MercadoPago Public Key', required_if_provider='mercadopago')
    mercadopago_access_token = fields.Char('MercadoPago Access Token', required_if_provider='mercadopago')

    # @api.onchange('provider', 'check_validity')
    # def onchange_check_validity(self):
    #     if self.provider == 'mercadopago' and self.check_validity:
    #         self.check_validity = False
    #         return {'warning': {
    #             'title': _("Warning"),
    #             'message': ('This option is not supported for MercadoPago')}}

    def mp_connect(self):
        self.ensure_one()
        MP = mercadopago.MP(self.mercadopago_access_token)
        MP = mercadopago.MP('TEST-2775253347293690-081210-4dede21e22738444d5fe2f092ee478f3__LC_LB__-113996959')
        # MP = mercadopago.MP(self.mercadopago_client_id, self.mercadopago_secret_key)
        environment = self.state == 'enabled' and 'prod' or 'test'
        if environment == "prod":
            MP.sandbox_mode(False)
        else:
            MP.sandbox_mode(True)
        return MP

    def action_client_secret(self):
        return True

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerMercadoPago, self)._get_feature_support()
        res['tokenize'].append('mercadopago')
        return res

    def _get_mercadopago_urls(self, environment):
        """ MercadoPago URLs """
        import pdb; pdb.set_trace()
        if environment == 'prod':
            return {'mercadopago_form_url': 'https://www.mercadopago.com.ar/'}
        else:
            return {'mercadopago_form_url': 'https://www.mercadopago.com.ar/'}

    def mercadopago_form_generate_values(self, values):
        self.ensure_one()
        mercadopago_tx_values = dict(values)
        base_url = self.get_base_url()
        import pdb; pdb.set_trace()

        temp_mercadopago_tx_values = {
            # 'x_login': self.mercadopago_login,
            'x_amount': float_repr(values['amount'], values['currency'].decimal_places if values['currency'] else 2),
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE' if not self.capture_manually else 'AUTH_ONLY',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            # 'x_relay_url': urls.url_join(base_url, MercadoPagoController._success_url),
            # 'x_cancel_url': urls.url_join(base_url, MercadoPagoController._failure_url),
            'x_currency_code': values['currency'] and values['currency'].name or '',
            'address': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').name or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'phone': values.get('partner_phone'),
            'billing_address': values.get('billing_partner_address'),
            'billing_city': values.get('billing_partner_city'),
            'billing_country': values.get('billing_partner_country') and values.get(
            'billing_partner_country').name or '',
            'billing_email': values.get('billing_partner_email'),
            'billing_zip_code': values.get('billing_partner_zip'),
            'billing_first_name': values.get('billing_partner_first_name'),
            'billing_last_name': values.get('billing_partner_last_name'),
            'billing_phone': values.get('billing_partner_phone'),
        }
        mercadopago_tx_values.update(temp_mercadopago_tx_values)
        import pdb; pdb.set_trace()
        return mercadopago_tx_values

    def mercadopago_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        import pdb; pdb.set_trace()
        return self._get_mercadopago_urls(environment)['mercadopago_form_url']

    @api.model
    def mercadopago_s2s_form_process(self, data):
        import pdb; pdb.set_trace()
        values = {
            'acquirer_id': 13,#int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id')),
            'token': data.get('token'),
            'payment_method_id': data.get('payment_method_id'),
            'issuer_id': data.get('issuer_id')
        }
        # Una vez cargada la tarjeta y validado el pago
        # Creamos un customer asociado a la tarjeta y creamos el token
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    def mercadopago_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["token", "payment_method_id", "installments", "issuer_id"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return False if error else True


class PaymentTransactionMercadoPago(models.Model):
    _inherit = 'payment.transaction'

    # TODO: This fields probably will be deleted
    mercadopago_txn_id = fields.Char('Transaction ID')
    mercadopago_txn_type = fields.Char('Transaction type', help='Informative field computed after payment')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _mercadopago_form_get_tx_from_data(self, data):
        """ Given a data dict coming from mercadopago, verify it and find the related
        transaction record.
        """
        import pdb; pdb.set_trace()
        pass

    def _mercadopago_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        import pdb; pdb.set_trace()
        return invalid_parameters

    def _mercadopago_form_validate(self, data):
        import pdb; pdb.set_trace()
        return False

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def mercadopago_s2s_do_transaction(self, **data):
        import pdb; pdb.set_trace()
        self.ensure_one()
        return False

    def mercadopago_s2s_do_refound(self, **data):
        import pdb; pdb.set_trace()
        self.ensure_one()
        return False

    def mercadopago_s2s_capture_transaction(self):
        import pdb; pdb.set_trace()
        self.ensure_one()
        return False

    def mercadopago_s2s_void_transaction(self):
        import pdb; pdb.set_trace()
        self.ensure_one()
        return False

    def mercadopago_s2s_get_tx_status(self):
        import pdb; pdb.set_trace()
        self.ensure_one()
        return False


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    save_token = fields.Char(string='Token', readonly=True)
    mercadopago_payment_method = fields.Char('Payment Method ID')

    @api.model
    def mercadopago_create(self, values):
        import pdb; pdb.set_trace()
        if values.get('token') and values.get('payment_method_id'):
            payment_method = values.get('payment_method_id')
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            partner = self.env['res.partner'].browse(values['partner_id'])
            token = values.get('token')
            partner_vals = {'email': partner.email}

            # buscamos / creamos un customer
            # MP = MercadoPagoAPI(acquirer)
            MP = acquirer.mp_connect()
            customers = MP.customer.search(partner_vals).get('response', {}).get('results', [])
            if len(customers) > 1:
                # TODO handle
                raise UserError('asdas')
            # customers
            # customerId = MP.customer.search(partner_vals).get('response', {}).get('results', {}).get('id')
            elif not customers:
            # if not customer or not customer.get('response', {}).get('results'):
                res = MP.customer.create(partner_vals)
                if not res or res.get('status') != '201':
                    # response.message, response.cause
                    raise ValidationError('ERROR"')
                customerId = res.get('response', {}).get('results', {}).get('id')
                # customer = MP.customer.search({'email': partner.email})
                # if not res or not res.get('response')
                # customer_id = res['id']
            else:
                customerId = customers[0].get('id')



            # /TODO chequear card existente
            # TODO ver si arregalmos liberria para poder llamar al card.create
            # card = MP.card.create({'token': token, 'customer_id': customerId})
            card = MP.customer.get_rest_client().post("/v1/customers/%s/cards?access_token=%s" % (customerId, MP.customer.get_access_token()),{'token': token})
            if not card or card.get('status') != '201':
                # error
                raise ValidationError('error al crear tarjeta')

            # buscamos / guardamos la tarjeta
            # card = None  # TODO: delete this
            # cards = MP.get_customer_cards(customer_id)
            # if card not in cards:
            #     card = MP.create_customer_card(customer_id, token)

        #     if not card:
        #         raise ValidationError(_('The Card creation in MercadoPago failed.'))


        #     # creo el token
            return {
                'name': '%s: ' + 'XXXX XXXX XXXX %s' % (payment_method, card.get('response')['last_four_digits']),
                'acquirer_ref': card.get('response')['id'],
                'mercadopago_payment_method': payment_method,
                'verified': True
            }
        # else:
        #     raise ValidationError(_('The Token creation in MercadoPago failed.'))
        else:
            return values
