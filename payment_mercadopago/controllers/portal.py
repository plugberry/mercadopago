from odoo.http import request
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(self, *args, sale_order_id=None, custom_create_values=None, **kwargs):
        if 'mercadopago_tmp_token' in kwargs:
            custom_create_values.update(mercadopago_tmp_token=kwargs.pop('mercadopago_tmp_token'))
        return super()._create_transaction(
            *args, sale_order_id=sale_order_id, custom_create_values=custom_create_values, **kwargs
        )

