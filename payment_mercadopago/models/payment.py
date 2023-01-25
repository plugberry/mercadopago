# coding: utf-8
from .mercadopago_request import MercadoPagoAPI
import logging
import urllib.parse as urlparse
import werkzeug

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.payment.models.payment_acquirer import ValidationError

from odoo.http import request
from ..controllers.main import MercadoPagoController
from datetime import datetime, timedelta
import requests


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
    mercadopago_capture_method = fields.Selection([
        ('deferred_capture', 'Deferred capture is posible'),
        ('refund_payment', 'Always refund payment')
        ],
        string='Capture method',
        default='deferred_capture'
    )
    mercadopago_binary = fields.Boolean('Use binary mode', default=True)

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
        res['fees'].append('mercadopago')
        return res

    def get_mercadopago_request(self):
        return MercadoPagoAPI(self)

    def mercadopago_compute_fees(self, amount, currency_id, country_id):
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = percentage / 100.0 * amount + fixed
        return fees

    def mercadopago_form_generate_values(self, values):
        self.ensure_one()
        tx_values = dict(values)
        base_url = self.get_base_url()

        success_url = MercadoPagoController._success_url
        failure_url = MercadoPagoController._failure_url
        pending_url = MercadoPagoController._pending_url
        return_url = tx_values.get('return_url')
        # si hay return_url se la pasamos codificada asi cuando vuelve
        # nos devuelve la misma
        if return_url:
            url_suffix = '{}{}'.format('?', werkzeug.urls.url_encode({'return_url': return_url}))
            success_url += url_suffix
            failure_url += url_suffix
            pending_url += url_suffix

        # TODO, implement, not implemented yet because mercadopago only
        # shows description of first line and we would need to send taxes too
        # sale_order = self.env['sale.order'].search(
        #     [('name', '=', tx_values["reference"])], limit=1)
        # if self.mercadopago_description == 'so_lines' and sale_order:
        #     items = [{
        #         "title": line.name,
        #         "quantity": line.product_uom_qty,
        #         "currency_id": (
        #             tx_values['currency'] and
        #             tx_values['currency'].name or ''),
        #         "unit_price": line.price_unit,
        #     } for line in sale_order.order_line]
        # else:
        items = [{
            "title": _("Order %s") % (tx_values["reference"]),
            "quantity": 1,
            "currency_id": (tx_values['currency'] and tx_values['currency'].name or ''),
            "unit_price": tx_values["amount"]
        }]

        if self.fees_active:
            items.append({
                "title": _('Recargo por Mercadopago'),
                "quantity": 1,
                "currency_id": (tx_values['currency'] and tx_values['currency'].name or ''),
                "unit_price": tx_values.pop('fees', 0.0)
            })

        preference = {
            "items": items,
            "payer": {
                "name": values["billing_partner_first_name"],
                "surname": values["billing_partner_last_name"],
                "email": values["partner_email"]
            },
            "back_urls": {
                "success": '%s' % urlparse.urljoin(base_url, success_url),
                "failure": '%s' % urlparse.urljoin(base_url, failure_url),
                "pending": '%s' % urlparse.urljoin(base_url, pending_url)
            },
            "notification_url": '%s' % urlparse.urljoin(self.get_base_url(), '/payment/mercadopago/notify/%s?source_news=webhooks' % self.id),
            "auto_return": "approved",
            "external_reference": tx_values["reference"],
        }
        preference.update(self.mercadopago_preference_date_due(tx_values))
        tx_values.update({
            'acquirer_id': self.id,
            'mercadopago_preference': preference
        })
        return tx_values

    def mercadopago_get_form_action_url(self):
        self.ensure_one()
        return MercadoPagoController._create_preference_url

    @api.model
    def mercadopago_preference_date_due(self, tx_values):
        expires_days = int(self.env['ir.config_parameter'].sudo().get_param('mercadopago.preference_expires_days', '0')) 
        return {'date_of_expiration':
                (datetime.now() + timedelta(days=expires_days)).isoformat()
        } if expires_days else {"expires": False}

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
            _logger.error(error)
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
        cvv_token = None
        if request:
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

        # Busco el customer en el result de MP en ves de pedirlo por el emai porque
        # hay casos la creacion del payer es mas lenta que la del pago y si lo pedimos nos dice que no existe
        # Pero hay casos donde payer o id no estan definidos en el result. para esos casos los busco en la funcion update
        customer_id = tree.get('payer', {}).get('id', False)
        if status_code in ["approved"]:
            init_state = self.state
            self.write({
                'acquirer_reference':  str(tree.get('id')),
                'date': fields.Datetime.now(),
            })
            self._set_transaction_done()
            if init_state != 'authorized':
                self.execute_callback()
            res = True

        # TODO: deberíamos separar este caso? sería cuando validamos tarjeta
        elif status_code == "authorized" and status_detail == "pending_capture":
            self._set_transaction_done()
            res = True
        elif status_code in ["in_process", "pending", "authorized"]:
            self.write({'acquirer_reference': tree.get('id')})
            self._set_transaction_pending()
            res = True
        elif status_code == "cancelled" and status_detail in ['by_collector', 'expired']:
            # TODO: Cancelamos la reserva para validación
            # Hay que hacer algo más del lado de Odoo?
            self._set_transaction_cancel()
            return True
        elif status_code == "rejected":
            try:
                error = ERROR_MESSAGES[status_detail] % self.payment_token_id.acquirer_ref
            except TypeError:
                error = ERROR_MESSAGES[status_detail]
            _logger.error(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            res = False
        else:
            error = "Error en la transacción"
            _logger.error(error)
            self.write({
                'acquirer_reference': tree.get('id'),
            })
            self._set_transaction_error(msg=error)
            res = False

        if self.payment_token_id:
            if self.payment_token_id.save_token:
                if not self.payment_token_id.verified:
                    self.payment_token_id.mercadopago_update(customer_id)
            else:
                self.payment_token_id.unlink()

        return res

    def action_mercadopago_refund(self):
        '''
        Free the captured amount
        '''
        for rec in self.filtered(lambda x: x.acquirer_id.provider == 'mercadopago'):
            MP = MercadoPagoAPI(rec.acquirer_id)
            resp = MP.ensure_payment_refund(int(self.acquirer_reference))

    def mercadopago_s2s_do_refund(self, **data):
        '''
        Free the captured amount
        '''
        MP = MercadoPagoAPI(self.acquirer_id)
        # por ahora desactivo esto
        # MP.ensure_payment_refund(int(self.acquirer_reference))

    def get_tx_info_from_mercadopago(self):
        txt = []
        for rec in self:
            if rec.acquirer_id.provider != 'mercadopago':
                continue
            MP = MercadoPagoAPI(rec.acquirer_id)

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
                    rec._mercadopago_s2s_validate_tree(payment)
                except:
                    _logger.error('cant validate_tree')
        self.env.cr.commit()
        raise UserError("%s" % ' \n'.join(txt))


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    email = fields.Char('Email', readonly=True)
    issuer = fields.Char('Issuer', readonly=True)
    customer_id = fields.Char('MercadoPago Customer', readonly=True)
    save_token = fields.Boolean('Save Token', default=True, readonly=True)
    token = fields.Char('Token', readonly=True)
    installments = fields.Integer('Installments', readonly=True)


    VALIDATION_AMOUNTS = {
        'CAD': 2.45,
        'EUR': 1.50,
        'GBP': 1.00,
        'JPY': 200,
        'AUD': 2.00,
        'NZD': 3.00,
        'CHF': 3.00,
        'HKD': 15.00,
        'SEK': 15.00,
        'DKK': 12.50,
        'PLN': 6.50,
        'NOK': 15.00,
        'HUF': 400.00,
        'CZK': 50.00,
        'BRL': 4.00,
        'MYR': 10.00,
        'MXN': 20.00,
        'ILS': 8.00,
        'PHP': 100.00,
        'TWD': 70.00,
        'THB': 70.00,
        'ARS': 5.00,
        'USD': 2.00
        }



    @api.model
    def mercadopago_create(self, values):
        if values.get('token') and values.get('payment_method_id'):
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

    def mercadopago_update(self, customer_id=False):
        # buscamos / creamos un customer si no viene desde el res de MP
        MP = MercadoPagoAPI(self.acquirer_id)
        if not customer_id:
            customer_id = MP.get_customer_profile(self.email)

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

    def unlink(self):
        for token in self:
            if token.acquirer_id.provider == 'mercadopago':
                mercado_pago = MercadoPagoAPI(token.acquirer_id)
                customer_id = mercado_pago.get_customer_profile(self.partner_id.email)

                mercado_pago.unlink_card_token(customer_id, token.token)

        return super().unlink()
