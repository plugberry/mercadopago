odoo.define('pos_mercadopago_point.CreditCardInstallmentButton', function (require) {
'use strict';


    const CreditCardInstallmentButton = require('pos_credit_card_installment.CreditCardInstallmentButton');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;

    const CreditCardInstallmentButtonMPPoint = CreditCardInstallmentButton => class extends CreditCardInstallmentButton {

        async onClick() {
            const order = this.env.pos.get_order();
            const installment = this.env.pos.installment;
            if (order.selected_paymentline.payment_method.use_payment_terminal === "mp_point"){
                if (order.selected_paymentline.amount > 0){
                    rpc.query({
                        model: 'pos.order',
                        method: 'make_payment_mp_point',
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
                            order.payment_point_ref_id = vals['payment_id']
                            order.token_point_ref_id = vals['token_id']
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
                        method: 'make_refunds_mp_point',
                        args: [[], {'amount_total': order.selected_paymentline.amount, 'payment_method_id': order.selected_paymentline.payment_method.id, 'pos_session_id':order.pos_session_id, 'toRefundLines_ids': toRefundLines_ids}],
                    }).then(function (vals){
                        if (vals['status_code'] !== 200){
                            Gui.showPopup('ErrorPopup', {
                                title: _t(vals['error']),
                                body: _t(vals['message']),
                            });
                        } else {
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

    Registries.Component.extend(CreditCardInstallmentButton, CreditCardInstallmentButtonMPPoint);
    return CreditCardInstallmentButton;

});
