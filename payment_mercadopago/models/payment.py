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
from odoo.http import request
# from odoo.addons.payment_mercadopago.controllers.sdk-python.mercadopago import
# from ..controllers.main import MercadoPagoController
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    'cc_rejected_bad_filled_card_number':   _("Revisa el número de tarjeta."),
    'cc_rejected_bad_filled_date':          _("Revisa la fecha de vencimiento."),
    'cc_rejected_bad_filled_other':         _("Revisa los datos."),
    'cc_rejected_bad_filled_security_code': _("Revisa el código de seguridad de la tarjeta."),
    'cc_rejected_blacklist':                _("No pudimos procesar tu pago."),
    'cc_rejected_call_for_authorize':       _("Debes autorizar ante %s el pago de %s."),
    'cc_rejected_card_disabled':            _("Llama a %s para activar tu tarjeta o usa otro medio de pago.\nEl teléfono está al dorso de tu tarjeta."),
    'cc_rejected_card_error':               _("No pudimos procesar tu pago."),
    'cc_rejected_duplicated_payment':       _("Ya hiciste un pago por ese valor.\nSi necesitas volver a pagar usa otra tarjeta u otro medio de pago."),
    'cc_rejected_high_risk':                _("Tu pago fue rechazado.\nElige otro de los medios de pago, te recomendamos con medios en efectivo."),
    'cc_rejected_insufficient_amount':      _("Tu %s no tiene fondos suficientes."),
    'cc_rejected_invalid_installments':     _("%s no procesa pagos en installments cuotas."),
    'cc_rejected_max_attempts':             _("Llegaste al límite de intentos permitidos.\nElige otra tarjeta u otro medio de pago."),
    'cc_rejected_other_reason':             _("%s no procesó el pago.")
}


class PaymentAcquirerMercadoPago(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('mercadopago', 'MercadoPago')])
    mercadopago_publishable_key = fields.Char('MercadoPago Public Key', required_if_provider='mercadopago')
    mercadopago_access_token = fields.Char('MercadoPago Access Token', required_if_provider='mercadopago')

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
        import pdb; pdb.set_trace()
        mercadopago_tx_values = dict(values)
        base_url = self.get_base_url()

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
        values = {
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id')),
            'token': data.get('token'),
            'payment_method_id': data.get('payment_method_id'),
            'issuer_id': data.get('issuer_id'),
            'save_token': data.get('save_token')
        }
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    def mercadopago_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["token", "payment_method_id"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return False if error else True


class PaymentTransactionMercadoPago(models.Model):
    _inherit = 'payment.transaction'

    # TODO: This fields probably will be deleted
    # mercadopago_txn_id = fields.Char('Transaction ID')
    # mercadopago_txn_type = fields.Char('Transaction type', help='Informative field computed after payment')

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
        self.ensure_one()
        MP = MercadoPagoAPI(self.acquirer_id)
        cvv_token = request.session.get('cvv_token')
        capture = self.type != 'validation'
        # TODO: revisar, si es validación el amount es 1.5 (viene de Odoo)
        if cvv_token:
            res = MP.payment(self.payment_token_id, round(self.amount, self.currency_id.decimal_places), capture, cvv_token)
            request.session.pop('cvv_token')
        else:
            res = MP.payment(self.payment_token_id, round(self.amount, self.currency_id.decimal_places), capture)
        return self._mercadopago_s2s_validate_tree(res)

    def _mercadopago_s2s_validate_tree(self, tree):
        if self.state == 'done':
            _logger.warning('MercadoPago: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = tree.get('status')
        status_detail = tree.get('status_detail')
        # TODO: revisar bien casos aprobados.
        #   - Pago normal: approved
        #   - Pago de autorización: authorized
        #   - En proceso de pago: in_process
        # We should check the "status_detail"?
        # in the case of capture payment would be: "pending_capture"
        import pdb; pdb.set_trace()
        if status_code in ["approved", "authorized", "in_process"]:
            init_state = self.state
            self.write({
                'acquirer_reference': tree.get('id'),
                'date': fields.Datetime.now(),
            })

            self._set_transaction_done()

            if init_state != 'authorized':
                self.execute_callback()

            if self.payment_token_id:
                if self.payment_token_id.save_token:
                    if not self.payment_token_id.verified:
                        self.payment_token_id.mercadopago_update(self.acquirer_id)
                else:
                    self.payment_token_id.name = "MercadoPago DELETED"
                    self.payment_token_id.active = False

            return True
        elif status_code == "cancelled" and status_detail == 'by_collector':
            # TODO: Cancelamos la reserva para validación
            # Hay que hacer algo más del lado de Odoo?
            return True
        elif status_code == "rejected":
            error = ERROR_MESSAGES[status_detail]
            _logger.info(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            return False
        # TODO: desarrollar casos de estados no aprobados
        # elif status_code == self._authorize_pending_tx_status:
        #     self.write({'acquirer_reference': tree.get('x_trans_id')})
        #     self._set_transaction_pending()
        #     return True
        else:
            error = "Error en la transacción"
            _logger.info(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            return False

    def mercadopago_s2s_do_refund(self, **data):
        '''
        Free the captured amount
        '''
        MP = MercadoPagoAPI(self.acquirer_id)
        MP.payment_cancel(self.acquirer_reference)
        # return False

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

    email = fields.Char('Email', readonly=True)
    save_token = fields.Boolean('Save Token', default=True, readonly=True)
    token = fields.Char('Token', readonly=True)

    @api.model
    def mercadopago_create(self, values):
        if values.get('token') and values.get('payment_method_id'):
            payment_method = values.get('payment_method_id')
            partner = self.env['res.partner'].browse(values['partner_id'])
            token = values.get('token')
            save_token = False if values.get('save_token') == "false" else True

            # create the token
            return {
                'name': "MercadoPago card token",
                'acquirer_ref': payment_method,
                'email': partner.email,
                'save_token': save_token,
                'token': token
            }
        # else:
        #     raise ValidationError(_('The Token creation in MercadoPago failed.'))
        else:
            return values

    def mercadopago_update(self, acquirer):
        # buscamos / creamos un customer
        MP = MercadoPagoAPI(acquirer)
        customer_id = MP.get_customer_profile(self.email)
        if not customer_id:
            customer_id = MP.create_customer_profile(self.email)

        # buscamos / guardamos la tarjeta
        card = None  # TODO: delete this
        cards = MP.get_customer_cards(customer_id)
        if card not in cards:
            card = MP.create_customer_card(customer_id, self.token)

        self.name = "%s: XXXX XXXX XXXX %s" % (self.acquirer_ref, card['last_four_digits'])
        self.token = card['id']
        self.verified = True
