# coding: utf-8
from .mercadopago_request import MercadoPagoAPI
import logging

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    'cc_rejected_bad_filled_card_number': _("Revisa el número de tarjeta."),
    'cc_rejected_bad_filled_date': _("Revisa la fecha de vencimiento."),
    'cc_rejected_bad_filled_other': _("Revisa los datos."),
    'cc_rejected_bad_filled_security_code': _("Revisa el código de seguridad de la tarjeta."),
    'cc_rejected_blacklist': _("No pudimos procesar tu pago."),
    'cc_rejected_call_for_authorize': _("Debes autorizar el pago ante %s."),
    'cc_rejected_card_disabled': _("Llama a %s para activar tu tarjeta o usa otro medio de pago.\nEl teléfono está al dorso de tu tarjeta."),
    'cc_rejected_card_error': _("No pudimos procesar tu pago."),
    'cc_rejected_duplicated_payment': _("Ya hiciste un pago por ese valor.\nSi necesitas volver a pagar usa otra tarjeta u otro medio de pago."),
    'cc_rejected_high_risk': _("Tu pago fue rechazado.\nElige otro de los medios de pago, te recomendamos con medios en efectivo."),
    'cc_rejected_insufficient_amount': _("Tu %s no tiene fondos suficientes."),
    'cc_rejected_invalid_installments': _("%s no procesa pagos en esa cantidad de cuotas."),
    'cc_rejected_max_attempts': _("Llegaste al límite de intentos permitidos.\nElige otra tarjeta u otro medio de pago."),
    'cc_rejected_other_reason': _("%s no procesó el pago.")
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

    @api.model
    def mercadopago_s2s_form_process(self, data):
        values = {
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id')),
            'token': data.get('token'),
            'payment_method_id': data.get('payment_method_id'),
            'email': data.get('email'),
            'issuer': data.get('issuer'),
            'installments': data.get('installments'),
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

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def mercadopago_s2s_do_transaction(self, **data):
        self.ensure_one()
        MP = MercadoPagoAPI(self.acquirer_id)

        # CVV_TOKEN:
        # If the token is not verified then is a new card so we have de cvv_token in the self.payment_token_id.token
        # If not, if the payment cames from token WITH cvv the cvv_token will be in the session.
        # Else, we do not have cvv_token, it's a payment without cvv
        cvv_token = request.session.pop('cvv_token', None) if self.payment_token_id.verified else self.payment_token_id.token
        capture = self.type != 'validation'

        # TODO: revisar, si es validación el amount es 1.5 (viene de Odoo)
        res = MP.payment(self.acquirer_id, self.payment_token_id, round(self.amount, self.currency_id.decimal_places), capture, cvv_token)

        return self._mercadopago_s2s_validate_tree(res)

    def _mercadopago_s2s_validate_tree(self, tree):
        if self.state == 'done':
            _logger.warning('MercadoPago: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = tree.get('status')
        status_detail = tree.get('status_detail')

        if status_code in ["approved", "authorized"]:
            init_state = self.state
            self.write({
                'acquirer_reference': tree.get('id'),
                'date': fields.Datetime.now(),
            })
            self._set_transaction_done()
            for order in self.sale_order_ids:
                order.client_order_ref = _("MercadoPago ID: %s" % tree.get('id'))
            if init_state != 'authorized':
                self.execute_callback()
            res = True

        # TODO: deberíamos separar este caso? sería cuando validamos tarjeta
        # elif status_code == "authorized" and status_detail == "pending_capture":
        #     self._set_transaction_authorized()
        #     return True
        elif status_code == "in_process":
            self.write({'acquirer_reference': tree.get('id')})
            self._set_transaction_pending()
            res = True
        elif status_code == "cancelled" and status_detail == 'by_collector':
            # TODO: Cancelamos la reserva para validación
            # Hay que hacer algo más del lado de Odoo?
            self._set_transaction_cancel()
            return True
        elif status_code == "rejected":
            try:
                error = ERROR_MESSAGES[status_detail] % self.payment_token_id.acquirer_ref.capitalize()
            except TypeError:
                error = ERROR_MESSAGES[status_detail]
            _logger.info(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            res = False
        else:
            error = "Error en la transacción"
            _logger.info(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            res = False

        if self.payment_token_id:
            if self.payment_token_id.save_token:
                if not self.payment_token_id.verified:
                    self.payment_token_id.mercadopago_update(self.acquirer_id)
            else:
                self.payment_token_id.unlink()

        return res

    def mercadopago_s2s_do_refund(self, **data):
        '''
        Free the captured amount
        '''
        MP = MercadoPagoAPI(self.acquirer_id)
        MP.payment_cancel(self.acquirer_reference)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    email = fields.Char('Email', readonly=True)
    issuer = fields.Char('Issuer', readonly=True)
    save_token = fields.Boolean('Save Token', default=True, readonly=True)
    token = fields.Char('Token', readonly=True)
    installments = fields.Integer('Installments', readonly=True)

    @api.model
    def mercadopago_create(self, values):
        if values.get('token') and values.get('payment_method_id'):
            # create the token
            return {
                'name': "MercadoPago card token",
                'acquirer_ref': values.get('payment_method_id'),
                'email': values.get('email'),
                'issuer': values.get('issuer'),
                'installments': int(values.get('installments', 1)),
                'save_token': values.get('save_token') == "on",
                'token': values.get('token'),
            }
        else:
            raise ValidationError(_('The Token creation in MercadoPago failed.'))

    def mercadopago_update(self, acquirer):
        # buscamos / creamos un customer
        MP = MercadoPagoAPI(acquirer)
        customer_id = MP.get_customer_profile(self.email)
        if not customer_id:
            customer_id = MP.create_customer_profile(self.email)

        # TODO: si un cliente tokeniza dos veces la misma tarjeta, debemos buscarla en MercadoPago o crearla nuevamente?
        # card = None  # TODO: delete this
        # cards = MP.get_customer_cards(customer_id)
        # if card not in cards:
        card = MP.create_customer_card(customer_id, self.token)

        self.name = "%s: XXXX XXXX XXXX %s" % (self.acquirer_ref.capitalize(), card['last_four_digits'])
        self.installments = 1
        self.token = card['id']
        self.verified = True

    def hide_email(self, email):
        username = email.split("@")[0]
        return(email.replace(username, username[:3] + "***"))
