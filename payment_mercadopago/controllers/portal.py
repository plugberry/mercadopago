from odoo.http import request
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(
        self, payment_option_id, reference_prefix, amount, currency_id, partner_id, flow,
        tokenization_requested, landing_route, is_validation=False,
        custom_create_values=None, **kwargs
    ):
        if 'mercadopago_tmp_token' in kwargs:
            custom_create_values = custom_create_values if custom_create_values else {}
            custom_create_values.update(mercadopago_tmp_token=kwargs.pop('mercadopago_tmp_token'))
        return super()._create_transaction( payment_option_id, reference_prefix, amount, currency_id, partner_id, flow,
            tokenization_requested, landing_route, is_validation=is_validation,
            custom_create_values=custom_create_values, **kwargs
        )

