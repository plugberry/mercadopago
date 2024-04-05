import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)



class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # Fields add by MercadoPago redirect
    # TODO: remove
    mercadopago_txn_id = fields.Char('Transaction ID')
    mercadopago_txn_type = fields.Char('Transaction type', help='Informative field computed after payment')
    # ----------------------------------

    mercadopago_tmp_token = fields.Char('MercadoPago temporal token')

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as acquirer-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'mercadopago':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }

    def _mercadopago_create_transaction_request(self, kwargs):
        """ Create an MercadoPago payment transaction request.

        Note: self.ensure_one()

        :param dict kwargs: token returned by MercadoPago, issuer, installments and payer email,
        :return:
        """
        self.ensure_one()

        self.mercadopago_tmp_token = kwargs.get('mercadopago_token')
        mercadopago_API = self.provider_id._get_mercadopago_request()
        kwargs['validation'] = True if self.provider_id.capture_manually or self.operation == 'validation' else False
        return mercadopago_API.payment(self, form_data=kwargs)

    def _send_payment_request(self):
        """ Override of payment to send a payment request to MercadoPago.
            This method handles payments from token (w/ CVV) or from subscriptions (w/o CVV)

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'mercadopago':
            return

        if not self.token_id:
            raise UserError("MercadoPago: " + _("The transaction is not linked to a token."))

        mercadopago_API = self.provider_id._get_mercadopago_request()

        # If the payment comes from subscription we do not have the cvv: w/o cvv payment flow
        cvv = self.callback_model_id.model != "sale.subscription"

        res_content = mercadopago_API.payment(self, token=self.token_id, cvv=cvv)
        _logger.info("MercadoPago request response:\n%s", pprint.pformat(res_content))

        # Handle the payment request response
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_notification_data('mercadopago', feedback_data)

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to MercadoPago.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :param bool create_refund_transaction: Whether a refund transaction should be created or not
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        res = super()._send_refund_request(
            amount_to_refund=amount_to_refund,
        )
        if self.provider_code == 'mercadopago':
            # TODO: implement
            raise UserError("MercadoPago: _send_refund_request not implemented")
        return res

    def _send_void_request(self):
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'mercadopago':
            return

        # TODO: implement
        raise UserError("MercadoPago: _send_void_request not implemented")

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Find the transaction based on the feedback data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the acquirer
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        _logger.info("provider_code %s " % provider_code)
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'mercadopago':
            return tx

        reference = notification_data.get('external_reference', False)
        if not reference:
            reference = notification_data.get('reference', False)

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'mercadopago')])
        if not tx:
            raise ValidationError(
                "MercadoPago: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def get_tx_info_from_mercadopago(self):
        txt = []
        for rec in self:
            if rec.provider_id.code != 'mercadopago':
                continue
            MP = self.provider_id._get_mercadopago_request()

            payments = MP.mp.payment().search(filters = {'external_reference': rec.reference})
            for payment in payments['response']['results']:
                txt += ['---------------------------']
                txt += ["STATUS: %s" % payment['status']]
                txt += ["AMOUNT: %s" % payment['transaction_amount']]
                txt += ["description: %s" % payment['description']]
                txt += ['---------------------------']
                txt += ['%s: %s' % (x, payment[x]) for x in payment]
                txt += ['---------------------------']
                try:
                    rec._process_notification_data({'reference': rec.reference, 'response': payment})
                except:
                    _logger.error('cant validate_tree')
        self.env.cr.commit()
        raise UserError("%s" % ' \n'.join(txt))

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Authorize data.

        Note: self.ensure_one()

        :param dict notification_data: The feedback data sent by the provider
        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'mercadopago':
            return super()._process_notification_data(notification_data)
        response_content = notification_data.get('response')
        _logger.info(response_content)
        self.provider_reference = response_content.get('x_trans_id')
        status = response_content.get('status')
        message = self._get_mercadopago_response_msg(response_content)
        if status in ['approved', 'processed']:  # Approved
            if self.state != 'done':
                self._set_done()
            else:
                _logger.info('The TX %s is already done. Cant set done twise' % self.reference)
            if self.tokenize and not self.token_id:
                self._mercadopago_tokenize_from_feedback_data(response_content)
        elif status in ['authorized']:  # Authorized: the card validation is ok
            if self.operation == 'validation':
                # TODO: revisar si tenemos que hacer algo más
                self._set_done()
                if self.tokenize and not self.token_id:
                    self._mercadopago_tokenize_from_feedback_data(response_content)
        elif status in ['cancelled', 'refunded', 'charged_back', 'rejected']:  # Declined
            _logger.info('Received notification for MercadoPago payment %s: set as cancelled' % (self.reference))
            # Llamamos a set_error y no set_cancel porque si no Odoo no muestra el mensaje en el portal
            self._set_error(state_message=message)
        elif status in ['pending', 'in_process', 'in_mediation']:  # Held for Review
            _logger.info('Received notification for MercadoPago payment %s: set as pending' % (self.reference))
            self._set_pending(state_message=message)
        else:  # Error / Unknown code
            # TODO: check how to get the error message
            error_code = response_content.get('error')
            _logger.info("received data with invalid status code %s and error code %s", status, error_code)
            self._set_error(
                "MercadoPago: " + _(
                    "Received data with status code \"%(status)s\" and error code \"%(error)s\"",
                    status=status, error=error_code
                )
            )

    def _mercadopago_tokenize_from_feedback_data(self, data):
        """ Create a new token based on the feedback data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        self.ensure_one()

        mercadopago_API = self.provider_id._get_mercadopago_request()
        # TODO: podríamos pasar el objeto partner y enviar todos los datos disponibles
        customer_id = mercadopago_API.get_customer_profile(self.partner_id.email)
        if customer_id:
            #  si un cliente tokeniza dos veces la misma tarjeta, debemos buscarla en MercadoPago o crearla nuevamente?
            card = mercadopago_API.create_customer_card(customer_id, self.mercadopago_tmp_token)
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'payment_details': card['last_four_digits'],
                'provider_ref': data['payment_method_id'],
                'bin': card['first_six_digits'],
                'partner_id': self.partner_id.id,
                'card_token': card['id'],
                # TODO: chequear que el mail sea el correcto, parece que en modo test MercadoPago pone otro mail
                'email': data['payer']['email'],
                'customer_id': customer_id,
                'verified': True,
            })
            self.write({
                'token_id': token.id,
                'tokenize': False,
            })
            _logger.info(
                "created token with id %s for partner with id %s", token.id, self.partner_id.id
            )

    def _get_mercadopago_response_msg(self, data):
        """ Return the response status in the human language.

        :return: The response message
        :param dict data: MercadoPago transaction response
        """
        mercadopago_messages = {
            'accredited': _("¡Listo! Se acreditó tu pago. En tu resumen verás el cargo de {amount} como {statement_descriptor}."),
            'pending_contingency': _("Estamos procesando tu pago. No te preocupes, menos de 2 días hábiles te avisaremos por e-mail si se acreditó."),
            'pending_review_manual': _("Estamos procesando tu pago. No te preocupes, menos de 2 días hábiles te avisaremos por e-mail si se acreditó o si necesitamos más información."),
            'cc_rejected_bad_filled_card_number': _("Revisa el número de tarjeta."),
            'cc_rejected_bad_filled_date': _("Revisa la fecha de vencimiento."),
            'cc_rejected_bad_filled_other': _("Revisa los datos."),
            'cc_rejected_bad_filled_security_code': _("Revisa el código de seguridad de la tarjeta."),
            'cc_rejected_blacklist': _("No pudimos procesar tu pago, utiliza otra tarjeta."),
            'cc_rejected_call_for_authorize': _("Debes autorizar ante {payment_method_id} el pago de {amount}."),
            'cc_rejected_card_disabled': _("Llama a {payment_method_id} para activar tu tarjeta o usa otro medio de pago.\nEl teléfono está al dorso de tu tarjeta."),
            'cc_rejected_card_error': _("No pudimos procesar tu pago, revisa la información de la tarjeta."),
            'cc_rejected_duplicated_payment': _("Ya hiciste un pago por ese valor.\nSi necesitas volver a pagar usa otra tarjeta u otro medio de pago."),
            'cc_rejected_high_risk': _("No pudimos procesar tu pago, utiliza otra tarjeta."),
            'cc_rejected_insufficient_amount': _("Tu {payment_method_id} no tiene fondos suficientes."),
            'cc_rejected_invalid_installments': _("{payment_method_id} no procesa pagos en {installments} cuotas."),
            'cc_rejected_max_attempts': _("Llegaste al límite de intentos permitidos.\nElige otra tarjeta u otro medio de pago."),
            'cc_rejected_other_reason': _("{payment_method_id} no procesó el pago, utiliza otra tarjeta o contacta al emisor.")
        }
        status = data['status_detail']
        try:
            message = mercadopago_messages[status].format(
                payment_method_id=data.get('payment_method_id'),
                amount=data.get('transaction_amount'),
                statement_descriptor=data.get('statement_descriptor'),
                installments=data.get('installments')
            )
        except KeyError:
            _logger.warning("MercadoPago transaction with unknown status. Return default message.")
            message = None
        return message
