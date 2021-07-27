# -*- coding: utf-8 -*-

import time
from werkzeug import urls
from lxml import objectify

import odoo
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_mercadopago.controllers.main import MercadoPagoController
from odoo.tools import mute_logger


@odoo.tests.tagged('post_install', '-at_install')
class MercadoPagoCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(MercadoPagoCommon, self).setUp()

        # MercadoPago only support ARS
        self.currency_ars = self.env.ref('base.ARS')

        self.mercadopago = self.env.ref('payment_mercadopago.payment_acquirer_mercadopago')
        self.mercadopago.write({
            'state': 'test',
        })


@odoo.tests.tagged('form')
# @odoo.tests.tagged('post_install', '-at_install', '-standard', 'external', 'form')
class MercadoPagoForm(MercadoPagoCommon):

    def test_10_mercadopago_form_render(self):

        self.assertEqual(self.mercadopago.state, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        form_values = {
            'mercadopago_preference': {
                'auto_return': 'approved',
                'back_urls': {'failure': urls.url_join(base_url, MercadoPagoController._failure_url),
                              'pending': urls.url_join(base_url, MercadoPagoController._pending_url),
                              'success': urls.url_join(base_url, MercadoPagoController._success_url)},
                'expires': False,
                'external_reference': 'SO004',
                'items': [{'currency_id': 'ARS',
                           'quantity': 1,
                           'title': 'Order SO004',
                           'unit_price': 56.16},
                          {'currency_id': 'ARS',
                           'quantity': 1,
                           'title': 'Recargo por Mercadopago',
                           'unit_price': 0.0}],
                'payer': {'email': self.buyer.email,
                          'name': self.buyer.name.split(' ')[0],
                          'surname': self.buyer.name.split(' ')[1]},
            }
        }
        self.buyer_values.update(form_values)

        import pdb; pdb.set_trace()
        # render the button
        res = self.mercadopago.render('SO004', 56.16, self.currency_ars.id, values=self.buyer_values)
        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'MercadoPago: Found %d "data_set" input instead of 1' % len(data_set))
        # self.assertEqual(data_set[0].get('data-action-url'), '/payment/mercadopago/create_preference', 'MercadoPago: wrong data-action-url POST url')
        for el in tree.iterfind('input'):
            values = list(el.attrib.values())
            if values[1] in ['data_set', 'cmd', 'acquirer_id', 'mercadopago_preference']:
                continue
            self.assertEqual(
                values[2],
                form_values[values[1]],
                'Authorize: wrong value for input %s: received %s instead of %s' % (values[1], values[2], form_values[values[1]])
            )

    @mute_logger('odoo.addons.payment_mercadopago.models.payment', 'ValidationError')
    def test_20_mercadopago_form_management(self):
        pass
        # # be sure not to do stupid thing
        # self.assertEqual(self.mercadopago.state, 'test', 'test without test environment')

        # # typical data posted by mercadopago after client has successfully paid
        # mercadopago_post_data = {
        #     'orderID': u'test_ref_2',
        #     'STATUS': u'9',
        #     'CARDNO': u'XXXXXXXXXXXX0002',
        #     'PAYID': u'25381582',
        #     'CN': u'Norbert Buyer',
        #     'NCERROR': u'0',
        #     'TRXDATE': u'11/15/13',
        #     'IP': u'85.201.233.72',
        #     'BRAND': u'VISA',
        #     'ACCEPTANCE': u'test123',
        #     'currency': u'EUR',
        #     'amount': u'1.95',
        #     'SHASIGN': u'7B7B0ED9CBC4A85543A9073374589033A62A05A5',
        #     'ED': u'0315',
        #     'PM': u'CreditCard'
        # }

        # # should raise error about unknown tx
        # with self.assertRaises(ValidationError):
        #     self.env['payment.transaction'].form_feedback(mercadopago_post_data)

        # # create tx
        # tx = self.env['payment.transaction'].create({
        #     'amount': 1.95,
        #     'acquirer_id': self.mercadopago.id,
        #     'currency_id': self.currency_euro.id,
        #     'reference': 'test_ref_2-1',
        #     'partner_name': 'Norbert Buyer',
        #     'partner_country_id': self.country_france.id})
        # # validate it
        # tx.form_feedback(mercadopago_post_data)
        # # check state
        # self.assertEqual(tx.state, 'done', 'mercadopago: validation did not put tx into done state')
        # self.assertEqual(tx.mercadopago_payid, mercadopago_post_data.get('PAYID'), 'mercadopago: validation did not update tx payid')

        # # reset tx
        # tx = self.env['payment.transaction'].create({
        #     'amount': 1.95,
        #     'acquirer_id': self.mercadopago.id,
        #     'currency_id': self.currency_euro.id,
        #     'reference': 'test_ref_2-2',
        #     'partner_name': 'Norbert Buyer',
        #     'partner_country_id': self.country_france.id})

        # # now mercadopago post is ok: try to modify the SHASIGN
        # mercadopago_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        # with self.assertRaises(ValidationError):
        #     tx.form_feedback(mercadopago_post_data)

        # # simulate an error
        # mercadopago_post_data['STATUS'] = 2
        # mercadopago_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        # tx.form_feedback(mercadopago_post_data)
        # # check state
        # self.assertEqual(tx.state, 'cancel', 'mercadopago: erroneous validation did not put tx into error state')


@odoo.tests.tagged('s2s')
# @odoo.tests.tagged('post_install', '-at_install', '-standard', 's2s')
class MercadoPagoS2s(MercadoPagoCommon):
    def test_30_mercadopago_s2s(self):
        # be sure not to do stupid thing
        mercadopago = self.mercadopago
        self.assertEqual(mercadopago.state, 'test', 'test without test environment')

        # create payment method
        payment_token = self.env['payment.token'].create({
            'acquirer_id': mercadopago.id,
            'partner_id': self.buyer_id,
            'email': self.buyer.email,
            'installments': '1',
            'issuer': None,
            'payment_method_id': 'visa',
            'save_token': 'on',
            # This token was created from Odoo frontend using a user with the same email of self.buyer ("norbert.buyer@example.com")
            'token': '1627326444746',
            'verified': True,
        })

        # create normal s2s transaction
        transaction = self.env['payment.transaction'].with_context(from_test=True).create({
            'amount': 10,
            'acquirer_id': mercadopago.id,
            'type': 'server2server',
            'currency_id': self.currency_ars.id,
            'reference': 'test_ref_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.mercadopago_s2s_do_transaction()
        self.assertEqual(transaction.state, 'done',)

    # TODO: add s2s_do_transaction test to simulate a failure and other states
