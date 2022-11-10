odoo.define('payment_mercadopago.payment_form', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var _t = core._t;
    var error_messages = {
        '205': 'El número de la tarjeta de no puede estar vacío.',
        '208': 'La fecha de vencimiento no puede esta vacío.',
        '209': 'La fecha de vencimiento no puede esta vacío.',
        '212': 'El tipo de documento no puede ser vacío.',
        '214': 'El número de documento no puede ser vacío.',
        '221': 'El titular de la tarjeta no puede ser vacío.',
        '224': 'El código de seguridad no puede ser vacío.',
        'E301': 'Número de tarjeta inválido.',
        'E302': 'Código de seguridad inválido.',
        '316': 'Titular de la tarjeta inválido.',
        '322': 'Tipo de documento inválido.',
        '324': 'Número de documento inválido.',
        '325': 'Fecha de vencimiento inválida.',
        '326': 'Fecha de vencimiento inválida.',
        '0': 'Los datos ingresados no son válidos.',
    }

    PaymentForm.include({

        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                return ajax.loadJS("https://secure.mlstatic.com/sdk/javascript/v1/mercadopago.js");
            })
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

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
            var formID = acquirerForm[0].id;

            var doSubmit = false;
            document.getElementById(formID).addEventListener('submit', getCardToken);
            getCardToken(ev);

            function getCardToken(event){
                event.preventDefault();
                if(!doSubmit){
                    let $form = document.getElementById(formID);
                    window.Mercadopago.createToken($form, setCardTokenAndPay);
                    return false;
                }
            };

            function setCardTokenAndPay(status, response) {
                if (status == 200 || status == 201) {
                    let form = document.getElementById(formID);
                    let card = document.createElement('input');
                    card.setAttribute('name', 'token');
                    card.setAttribute('type', 'hidden');
                    card.setAttribute('value', response.id);
                    form.appendChild(card);
                    doSubmit=true;
                    var inputsForm = $('input', acquirerForm);
                    var formInputs = self.getFormData(inputsForm);
                    var selectForm = $('select', acquirerForm);
                    var formSelects = self.getFormData(selectForm);
                    var formData = {...formInputs,...formSelects}
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
                        let error_text = _t("We are not able to add your payment method at the moment.\n")
                        console.error(error)
                        if (error.message?.data?.message){
                            error_text = _t(error.message.data.message);
                        }
                        error.event.preventDefault();
                        acquirerForm.removeClass('d-none');
                        self.enableButton(button);
                        self.displayError(
                            _t('Error en su pago'), error_text
                        );
                    });
                } else {
                    acquirerForm.removeClass('d-none');
                    self.enableButton(button);
                    var error_msg = error_messages[response.cause[0].code];
                    if (error_msg === undefined)
                        error_msg = error_messages['0']
                    self.do_warn(_t("Server Error"),_t(error_msg));
                }
            };
        },

        /**
         * @param {Event} ev
         * @param {DOMElement} checkedRadio
         */
        _mercadoPagoOTP: function(ev, $checkedRadio) {
            var self = this;
            var button = ev.target;
            var form = this.el;
            var tokenID = $checkedRadio.val();

            // cvv form
            var $cvv_form = document.createElement("form");

            // card
            var card_id = $checkedRadio.data('card_id');
            let card = document.createElement('input');
            card.setAttribute('name', 'cardId');
            card.setAttribute('data-checkout', 'cardId');
            card.setAttribute('type', 'hidden');
            card.setAttribute('value', card_id);
            $cvv_form.appendChild(card);

            // cvv
            var cvv = document.getElementById('cc_cvc_' + tokenID);
            $cvv_form.appendChild(cvv);
            if (cvv.value.length < 3 ){
                self.do_warn(_t("Error"),_t(error_messages['E302']));
                return false;
            }
            this.disableButton(button);

            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            var formData = this.getFormData(inputsForm);
            window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);

            window.Mercadopago.createToken($cvv_form, function (status, response) {
                if (status == 200 || status == 201) {
                    var token = response.id;
                    // TODO: no debería ser necesario llamar a un controlador para esto
                    // session['cvv_token'] = token ?
                    self._rpc({
                        route: '/payment/mercadopago/s2s/otp',
                        params: {token: token}
                    }).then (function (data) {
                        // if the server has returned true
                        if (data.result) {
                            form.submit();
                        }
                    });
                } else {
                    self.enableButton(button);
                    self.do_warn(_t("Server Error"),_t("We are not able to process your payment at the moment.\n"));
                }
            });
        },

        // method to complete de form
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');

            if ($checkedRadio.length !== 1) {
                return;
            }
            if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {

                var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
                var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
                var inputsForm = $('input', acquirerForm);
                var formData = this.getFormData(inputsForm);
                window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);
                window.Mercadopago.getIdentificationTypes();
                document.getElementById('cc_number').addEventListener('change', guessPaymentMethod);

                function guessPaymentMethod(event) {
                    let cardnumber = document.getElementById("cc_number").value.split(" ").join("");
                    if (cardnumber.length >= 6) {
                        let bin = cardnumber.substring(0,6);
                        window.Mercadopago.getPaymentMethod({
                            "bin": bin
                        }, setPaymentMethod);
                    }
                    let issuerSelect = document.getElementById('issuer');
                    issuerSelect.classList.add("o_hidden");
                    let installments = document.getElementById('installments');
                    installments.classList.add("o_hidden");
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
                    }
                };

                function getIssuers(paymentMethodId) {
                    window.Mercadopago.getIssuers(
                        paymentMethodId,
                        setIssuers
                    );
                };

                function setIssuers(status, response) {
                    if (status == 200) {
                        let issuerSelect = document.getElementById('issuer');
                        issuerSelect.classList.remove("o_hidden");
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
                        let installments = document.getElementById('installments');
                        let show_installments = $(installments).data('show-installments');
                        if (show_installments)
                            installments.classList.remove("o_hidden");
                        installments.options.length = 0;
                        response[0].payer_costs.forEach( payerCost => {
                            let opt = document.createElement('option');
                            opt.text = payerCost.recommended_message;
                            opt.value = payerCost.installments;
                            installments.appendChild(opt);
                        });
                    } else {
                        alert(`installments method info error: ${response}`);
                    }
                };
            }
            this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        payEvent: function (ev) {
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
            // first we check that the user has selected a MercadoPago as s2s payment method
            if ($checkedRadio.length === 1 && $checkedRadio.data('provider') === 'mercadopago'){
                if (this.isNewPaymentRadio($checkedRadio))
                    return this._createMercadoPagoToken(ev, $checkedRadio);
                else if ($checkedRadio.data('cvv') === 'True')
                    return this._mercadoPagoOTP(ev, $checkedRadio);
                else
                    return this._super.apply(this, arguments);
            } else
                return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        addPmEvent: function (ev) {
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
