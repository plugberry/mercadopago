from odoo.http import request
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(self, custom_create_values, **kwargs):
        if 'mercadopago_tmp_token' in kwargs:
            custom_create_values.update(mercadopago_tmp_token=kwargs.pop('mercadopago_tmp_token'))
        return super()._create_transaction(custom_create_values=custom_create_values, **kwargs)

