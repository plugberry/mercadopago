odoo.define('payment_mercadopago.payment_form', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var _t = core._t;

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
            console.log('_createMercadoPagoToken');
            var self = this;
            if (ev.type === 'submit') {
                var button = $(ev.target).find('*[type="submit"]')[0]
            } else {
                var button = ev.target;
            }
            this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var formID = acquirerForm[0].id;

            var doSubmit = false;
            document.getElementById(formID).addEventListener('submit', getCardToken);
            getCardToken(ev);

            function getCardToken(event){
                console.log('getCardToken');
                event.preventDefault();
                if(!doSubmit){
                    let $form = document.getElementById(formID);
                    window.Mercadopago.createToken($form, setCardTokenAndPay);
                    return false;
                }
            };

            function setCardTokenAndPay(status, response) {
                console.log('setCardTokenAndPay');
                if (status == 200 || status == 201) {
                    console.log('setCardTokenAndPay 200');
                    let form = document.getElementById(formID);
                    let card = document.createElement('input');
                    card.setAttribute('name', 'token');
                    card.setAttribute('type', 'hidden');
                    card.setAttribute('value', response.id);
                    form.appendChild(card);
                    doSubmit=true;
                    // form.submit();
                    console.log('TODO: send_token');
                    var inputsForm = $('input', acquirerForm);
                    var formData = self.getFormData(inputsForm);
                    self._rpc({
                        route: formData.data_set,
                        params: formData
                    }).then (function (data) {
                        if (addPmEvent) {
                            if (formData.return_url) {
                                window.location = formData.return_url;
                            } else {
                                window.location.reload();
                            }
                        } else {
                            $checkedRadio.val(data.id);
                            self.el.submit();
                        }
                    }).guardedCatch(function (error) {
                        // if the rpc fails, pretty obvious
                        error.event.preventDefault();
                        acquirerForm.removeClass('d-none');
                        self.enableButton(button);
                        self.displayError(
                            _t('Server Error'),
                            _t("We are not able to add your payment method at the moment.") +
                                self._parseError(error)
                        );
                    });

                } else {
                    alert("Verify filled data!\n"+JSON.stringify(response, null, 4));
                }
            };
        },

    // method to complete de form
    updateNewPaymentDisplayStatus: function () {
        console.log('mp_updateNewPaymentDisplayStatus');
        var $checkedRadio = this.$('input[type="radio"]:checked');

        if ($checkedRadio.length !== 1) {
            return;
        }
        if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {

            window.Mercadopago.setPublishableKey("TEST-f68c38b9-ba2d-44bf-b6c6-23578cfde81a");
            console.log('set_pub_key');
            window.Mercadopago.getIdentificationTypes();
            document.getElementById('cc_number').addEventListener('change', guessPaymentMethod);

            function guessPaymentMethod(event) {
                console.log('guessPaymentMethod');
                let cardnumber = document.getElementById("cc_number").value.split(" ").join("");
                if (cardnumber.length >= 6) {
                    let bin = cardnumber.substring(0,6);
                    window.Mercadopago.getPaymentMethod({
                        "bin": bin
                    }, setPaymentMethod);
                }
            };

            function setPaymentMethod(status, response) {
                console.log('setPaymentMethod');
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
                console.log('getIssuers');
                window.Mercadopago.getIssuers(
                    paymentMethodId,
                    setIssuers
                );
            };

            function setIssuers(status, response) {
                console.log('setIssuers');
                if (status == 200) {
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
                console.log('getInstallments');
                window.Mercadopago.getInstallments({
                    "payment_method_id": paymentMethodId,
                    "amount": parseFloat(transactionAmount),
                    "issuer_id": issuerId ? parseInt(issuerId) : undefined
                }, setInstallments);
            };

            function setInstallments(status, response){
                console.log('setInstallments');
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
        }
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    payEvent: function (ev) {
        ev.preventDefault();
        console.log('HANDLER: payEvent');
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a MercadoPago as s2s payment method
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
        console.log('addPmEvent');
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a MercadoPago as add payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
            return this._createMercadoPagoToken(ev, $checkedRadio, true);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    });
});
