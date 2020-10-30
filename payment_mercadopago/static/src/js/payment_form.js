odoo.define('payment_mercadopago.payment_form', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var Dialog = require('web.Dialog');
    // TODO: es necesario esta línea (session)?
    // var session = require('web.session');
    var _t = core._t;
    var Qweb = core.qweb;
    // TODO hacer esto bien y que solo se ejecute en metodo click mercadopago
    console.log('p1');
    // # TODO hacer parametrizable

    PaymentForm.include({

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return ajax.loadJS("https://secure.mlstatic.com/sdk/javascript/v1/mercadopago.js");
            })
        },

        /**
         * called when clicking on pay now or add payment event to create token for credit card/debit card.
         *
         * @private
         * @param {Event} ev
         * @param {DOMElement} checkedRadio
         * @param {Boolean} addPmEvent
         */
        _createMercadoPagoToken: function(ev, $checkedRadio, addPmEvent) {
            var self = this;
            if (ev.type === 'submit') {
                var button = $(ev.target).find('*[type="submit"]')[0]
            } else {
                var button = ev.target;
            }
            this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            console.log('ddddddd');
            var formData = self.getFormData(inputsForm);
            // debugger;
            getCardToken();


// document.getElementById('paymentForm').addEventListener('submit', getCardToken);
function getCardToken(){
//    event.preventDefault();
console.log('asdasdas');
    //    let $form = document.getElementById('paymentForm');
    //    let $form = document.getElementById('paymentForm');
       let $form = document.getElementsByClassName("o_payment_form");

       window.Mercadopago.createToken($form, setCardTokenAndPay);
       return false;
};

function setCardTokenAndPay(status, response) {
   if (status == 200 || status == 201) {
       let form = document.getElementById('paymentForm');
       let card = document.createElement('input');
       card.setAttribute('name', 'token');
       card.setAttribute('type', 'hidden');
       card.setAttribute('value', response.id);
       form.appendChild(card);
       doSubmit=true;
       form.submit();
   } else {
       alert("Verify filled data!\n"+JSON.stringify(response, null, 4));
   }
};

            // templateLoaded.finally(
            //     function() {
            //         document.getElementById('cardNumber').addEventListener('change', guessPaymentMethod);
            //         console.log('ccccccccccc');
            //     })
            },

        addPmEvent: function(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');

            // first we check that the user has selected a authorize as add payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
                this._createMercadoPagoToken(ev, $checkedRadio, true);
            } else {
                this._super.apply(this, arguments);
            }
        },
        radioClickEvent: function (ev) {
            console.log('asdasda');
            // // radio button checked when we click on entire zone(body) of the payment acquirer
            // $(ev.currentTarget).find('input[type="radio"]').prop("checked", true);
            // this.updateNewPaymentDisplayStatus();
            // FROM MP https://www.mercadopago.com.ar/developers/es/guides/online-payments/checkout-api/receiving-payment-by-card
            window.Mercadopago.setPublishableKey("TEST-f68c38b9-ba2d-44bf-b6c6-23578cfde81a");
            window.Mercadopago.getIdentificationTypes();
            document.getElementById('cardNumber').addEventListener('change', guessPaymentMethod);
            function guessPaymentMethod(event) {
                let cardnumber = document.getElementById("cardNumber").value;
                if (cardnumber.length >= 6) {
                    let bin = cardnumber.substring(0,6);
                    window.Mercadopago.getPaymentMethod({
                        "bin": bin
                    }, setPaymentMethod);
                }
            };

            function setPaymentMethod(status, response) {
                if (status == 200) {
                    let paymentMethod = response[0];
                    document.getElementById('paymentMethodId').value = paymentMethod.id;

                    if(paymentMethod.additional_info_needed.includes("issuer_id")){
                        getIssuers(paymentMethod.id);
                    } else {
                        getInstallments(
                            paymentMethod.id,
                            document.getElementById('transactionAmount').value
                        );
                    }
                } else {
                    alert(`payment method info error: ${response}`);
                }
            };

            function getIssuers(paymentMethodId) {
                window.Mercadopago.getIssuers(
                    paymentMethodId,
                    setIssuers
                );
            };

            function setIssuers(status, response) {
                console.log('setIssuers');
                if (status == 200) {
                    console.log('setIssuers 200');
                    let issuerSelect = document.getElementById('issuer');
                    response.forEach( issuer => {
                        let opt = document.createElement('option');
                        opt.text = issuer.name;
                        opt.value = issuer.id;
                        issuerSelect.appendChild(opt);
                    });

                    getInstallments(
                        document.getElementById('paymentMethodId').value,
                        document.getElementById('transactionAmount').value,
                        issuerSelect.value
                    );
                } else {
                    alert(`issuers method info error: ${response}`);
                };
            };

            function getInstallments(paymentMethodId, transactionAmount, issuerId){
                window.Mercadopago.getInstallments({
                    "payment_method_id": paymentMethodId,
                    "amount": parseFloat(transactionAmount),
                    "issuer_id": issuerId ? parseInt(issuerId) : undefined
                }, setInstallments);
            };

            function setInstallments(status, response){
                if (status == 200) {
                    document.getElementById('installments').options.length = 0;
                    response[0].payer_costs.forEach( payerCost => {
                        let opt = document.createElement('option');
                        opt.text = payerCost.recommended_message;
                        opt.value = payerCost.installments;
                        document.getElementById('installments').appendChild(opt);
                    });
                } else {
                    alert(`installments method info error: ${response}`);
                }
            };

            this._super.apply(this, arguments);
        },
    /**
     * @override
     */
    payEvent: function (ev) {
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as s2s payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
            return this._createMercadoPagoToken(ev, $checkedRadio);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    addPmEvent: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a stripe as add payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
            return this._createMercadoPagoToken(ev, $checkedRadio, true);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    });
});
