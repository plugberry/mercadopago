odoo.define('pos_mercadopago_qr.CreditCardInstallmentButton', function (require) {
'use strict';

    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const CreditCardInstallmentButton = require('pos_credit_card_installment.CreditCardInstallmentButton');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;

    const CreditCardInstallmentButtonMPQR = CreditCardInstallmentButton => class extends CreditCardInstallmentButton {

        async onClick() {
            const order = this.env.pos.get_order();
            const installment = this.env.pos.installment;
            console.log('Entro al QR')
            if (order.selected_paymentline.payment_method.use_payment_terminal === "mp_qr"){
                if (order.selected_paymentline.amount > 0){
                    rpc.query({
                        model: 'pos.order',
                        method: 'make_payment_mp_qr',
                        args: [[], {'amount_total': order.selected_paymentline.amount,
                                    'payment_method_id': order.selected_paymentline.payment_method.id,
                                    'pos_session_id': order.pos_session_id,
                                    'access_token': order.access_token,
                                    'installment': installment,
                                    'order_name': order.name,
                                    'order_uid': order.uid,
                        }],
                    }).then(function (vals){
                        if (vals['status_code'] !== 200){
                            Gui.showPopup('ErrorPopup', {
                                title: _t('Error'),
                                body: _t(vals['error']),
                            });
                        } else {
                            return;
                        }
                    });
                }
                else{
                    const toRefundLines = this.env.pos.toRefundLines
                    let toRefundLines_ids = []
                    _.each(toRefundLines, function(line_id,index) {
                        toRefundLines_ids.push(line_id.orderline.orderBackendId);
                    })
                    rpc.query({
                        model: 'pos.order',
                        method: 'make_refunds_mp',
                        args: [[], {'amount_total': order.selected_paymentline.amount, 'payment_method_id': order.selected_paymentline.payment_method.id, 'pos_session_id':order.pos_session_id, 'toRefundLines_ids': toRefundLines_ids}],
                    }).then(function (vals){
                        if (vals['status_code'] !== 200){
                            Gui.showPopup('ErrorPopup', {
                                title: _t(vals['error']),
                                body: _t(vals['message']),
                            });
                        }
                        else{
                            order.mp_qr_payment_refound_token = vals['payment_id'];
                            return;
                        }
                    });
                }
            }
            else {
                super.onClick();
            }
        }

    }

    Registries.Component.extend(CreditCardInstallmentButton, CreditCardInstallmentButtonMPQR);
    return CreditCardInstallmentButton;

});
