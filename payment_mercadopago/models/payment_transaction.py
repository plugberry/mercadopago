# coding: utf-8
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse
import werkzeug

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from ..controllers.main import MercadoPagoController

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

class PaymentTransactionMercadoPago(models.Model):
    _inherit = 'payment.transaction'

    # Fields add by MercadoPago redirect
    mercadopago_txn_id = fields.Char('Transaction ID')
    mercadopago_txn_type = fields.Char('Transaction type', help='Informative field computed after payment')
    # ----------------------------------

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _mercadopago_form_get_tx_from_data(self, data):
        reference = data.get('external_reference')
        collection_id = data.get('collection_id')
        if not reference or not collection_id:
            error_msg = (
                'MercadoPago: received data with missing reference (%s) or '
                'collection_id (%s)' % (reference, collection_id))
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search(
            [('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = (
                'MercadoPago: received data for reference %s' % (reference))
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.model
    def _mercadopago_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        # TODO implementar invalid paramters desde
        # https://www.mercadopago.com.ar/developers/es/api-docs/basic-checkout/checkout-preferences/
        # if data.get('pspReference'):
        # _logger.ValidationError('Received a notification from MercadoLibre.')
        return invalid_parameters

    @api.model
    def _mercadopago_form_validate(self, data):
        """
        From:
        https://developers.mercadopago.com/documentacion/notificaciones-de-pago
        Por lo que vi nunca se devuelve la "cancel_reason" o "pending_reason"
        """
        status = data.get('collection_status')
        data = {
            'acquirer_reference': data.get('external_reference'),
            'mercadopago_txn_type': data.get('payment_type'),
            'mercadopago_txn_id': data.get('merchant_order_id', False),
            # otros parametros que vuelven son 'collection_id'
        }
        if status in ['approved', 'processed']:
            _logger.info('Validated MercadoPago payment for tx %s: set as done' % (self.reference))
            self.write(data)
            self._set_transaction_done()
            return True
        elif status in ['pending', 'in_process', 'in_mediation']:
            _logger.info('Received notification for MercadoPago payment %s: set as pending' % (self.reference))
            data.update(state_message=data.get('pending_reason', ''))
            self.write(data)
            self._set_transaction_pending()
            return True
        elif status in ['cancelled', 'refunded', 'charged_back', 'rejected']:
            _logger.info('Received notification for MercadoPago payment %s: set as cancelled' % (self.reference))
            data.update(state_message=data.get('cancel_reason', ''))
            self.write(data)
            self._set_transaction_cancel()
            return True
        else:
            error = (
                'Received unrecognized status for MercadoPago payment %s: %s, '
                'set as error' % (self.reference, status))
            _logger.info(error)
            data.update(state_message=error)
            self.write(data)
            self._set_transaction_error(error)
            return True

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
        res = MP.payment(self, round(self.amount, self.currency_id.decimal_places), capture, cvv_token)

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

