# -*- coding: utf-8 -*-

from lxml import objectify
import time

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_mercadopago.controllers.main import MercadoPagoController
from werkzeug import urls

from odoo.tools import mute_logger


class MercadoPayment(PaymentAcquirerCommon):

    def setUp(self):
        super(MercadoPayment, self).setUp()

        self.mercadopago = self.env.ref('payment_mercadopago.payment_acquirer_mercadopago')
        self.mercadopago.write({
            'state': 'test',
        })

    def test_10_mercadopago_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # be sure not to do stupid thing
        self.assertEqual(self.mercadopago.state, 'test', 'test without test environment')

    @mute_logger('odoo.addons.payment_mercadopago.models.payment', 'ValidationError')
    def test_20_mercadopago_form_management(self):
        # be sure not to do stupid thing
        self.assertEqual(self.mercadopago.state, 'test', 'test without test environment')

        # typical data posted by mercadopago after client has successfully paid
        mercadopago_post_data = {
            'orderID': u'test_ref_2',
            'STATUS': u'9',
            'CARDNO': u'XXXXXXXXXXXX0002',
            'PAYID': u'25381582',
            'CN': u'Norbert Buyer',
            'NCERROR': u'0',
            'TRXDATE': u'11/15/13',
            'IP': u'85.201.233.72',
            'BRAND': u'VISA',
            'ACCEPTANCE': u'test123',
            'currency': u'EUR',
            'amount': u'1.95',
            'SHASIGN': u'7B7B0ED9CBC4A85543A9073374589033A62A05A5',
            'ED': u'0315',
            'PM': u'CreditCard'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(mercadopago_post_data)

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.mercadopago.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2-1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})
        # validate it
        tx.form_feedback(mercadopago_post_data)
        # check state
        self.assertEqual(tx.state, 'done', 'mercadopago: validation did not put tx into done state')
        self.assertEqual(tx.mercadopago_payid, mercadopago_post_data.get('PAYID'), 'mercadopago: validation did not update tx payid')

        # reset tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.mercadopago.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2-2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # now mercadopago post is ok: try to modify the SHASIGN
        mercadopago_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        with self.assertRaises(ValidationError):
            tx.form_feedback(mercadopago_post_data)

        # simulate an error
        mercadopago_post_data['STATUS'] = 2
        mercadopago_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        tx.form_feedback(mercadopago_post_data)
        # check state
        self.assertEqual(tx.state, 'cancel', 'mercadopago: erroneous validation did not put tx into error state')

    def test_30_mercadopago_s2s(self):
        test_ref = 'test_ref_%.15f' % time.time()
        # be sure not to do stupid thing
        self.assertEqual(self.mercadopago.mercadopago_post_datastate, 'test', 'test without test environment')

        # create a new draft tx
        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.mercadopago.id,
            'currency_id': self.currency_euro.id,
            'reference': test_ref,
            'partner_id': self.buyer_id,
            'type': 'server2server',
        })

        # create an alias
        res = tx.mercadopago_s2s_create_alias({
            'expiry_date_mm': '01',
            'expiry_date_yy': '2021',
            'holder_name': 'TEst',
            'number': '5522336554122',
            'brand': 'VISA'})

        res = tx.mercadopago_s2s_execute({})
    
    
