odoo.define('pos_mercadopago_point.PaymentScreen', function (require) {
    'use strict';

    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const { Gui } = require('point_of_sale.Gui');
    const Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;

    const PosMPPointPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {

            async validateOrder(isForceValidate) {
                NumberBuffer.capture();
                const order = this.env.pos.get_order();
                if (order.selected_paymentline.payment_method.use_payment_terminal === "mp_point"){
                    var result = await rpc.query({
                        model: 'pos.order',
                        method: 'get_payment_status_mp_point',
                        args: [[], {'pos_session_id': order.pos_session_id, 'payment_method_id': order.selected_paymentline.payment_method.id, 'payment_point_ref_id': order.payment_point_ref_id,}],
                    })
                    if ((result['payment_status'] === 'approved') && result['status_code'] === 200){
                        order.mp_qr_payment_id = result['payment_id'];
                        var result_new = await super.validateOrder(...arguments);
                        return rpc.query({
                            model: 'pos.order',
                            method: 'updating_order_point',
                            args: [[], { 'mp_point_payment_id': result['payment_id'], 'access_token_order': order.access_token}],
                        });
                    }
                    if ((result['payment_status'] !== 'approved') && result['status_code'] === 200){
                        Gui.showPopup('ErrorPopup', {
                            title: _t('Aviso'),
                            body: _t('Debe ser realizada la transacción antes de ser validada!'),
                        });
                    }
                    if (result['status_code'] !== 200){
                        Gui.showPopup('ErrorPopup', {
                            title: _t('Error'),
                            body: _t(vals['error']),
                        });
                    }
                }
                else{
                    return super.validateOrder(...arguments);
                }
            }

            deletePaymentLine(event) {
                var self = this;
                const { cid } = event.detail;
                const order = this.env.pos.get_order();
                const line = this.paymentLines.find((line) => line.cid === cid);
                console.log('Entra al eliminar MP POINT')
                if (line.payment_method.use_payment_terminal === "mp_point"){
                    console.log('Entra al eliminar MP POINT IFI FII')
                    try {
                        rpc.query({
                            model: 'pos.order',
                            method: 'make_cancel_point',
                            args: [[], {'amount_total': line.amount, 'payment_method_id': line.payment_method.id, 'pos_session_id':line.order.pos_session_id, 'token_point_ref_id': order.token_point_ref_id, 'payment_point_ref_id': order.payment_point_ref_id}],
                        });
                    } catch (_e) {
                        Dialog.alert(this, _t("Error trying to connect to terminal. Check your internet connection"));
                    }

                    // If a paymentline with a payment terminal linked to
                    // it is removed, the terminal should get a cancel
                    // request.
                    if (['waiting', 'waitingCard', 'timeout'].includes(line.get_payment_status())) {
                        line.set_payment_status('waitingCancel');
                        line.payment_method.payment_terminal.send_payment_cancel(this.currentOrder, cid).then(function() {
                            self.currentOrder.remove_paymentline(line);
                            NumberBuffer.reset();
                            self.render(true);
                        })
                    }
                    else if (line.get_payment_status() !== 'waitingCancel') {
                        this.currentOrder.remove_paymentline(line);
                        NumberBuffer.reset();
                        this.render(true);
                    }
                } else {
                    console.log('Entra al eliminar MP POINT SUPER')
                    super.deletePaymentLine(event);
                }
            }
    };
    Registries.Component.extend(PaymentScreen, PosMPPointPaymentScreen);
    return PaymentScreen;
    });
