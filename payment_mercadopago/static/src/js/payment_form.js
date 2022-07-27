/* global Accept */
odoo.define('payment_mercadopago.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const ajax = require('web.ajax');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    var error_messages = {
        '205': 'El número de la tarjeta de no puede ser vacío.',
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

    const mercadopagoMixin = {

        start: function () {

            this._super(...arguments);
       },

        /**
         * Return all relevant inline form inputs based on the payment method type of the acquirer.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @param {string} flow - The online payment flow of the transaction
         * @return {Object} - An object mapping the name of inline form inputs to their DOM element
         */
         _MercadoPagoGetInlineFormInputs: function (acquirerId, flow) {
            if (flow === 'direct') {
                return {
                    card: document.getElementById(`o_mercadopago_card_number_${acquirerId}`),
                    month: document.getElementById(`o_mercadopago_month_${acquirerId}`),
                    year: document.getElementById(`o_mercadopago_year_${acquirerId}`),
                    code: document.getElementById(`o_mercadopago_code_${acquirerId}`),
                    holder: document.getElementById(`o_mercadopago_holder_${acquirerId}`),
                    vat: document.getElementById(`o_mercadopago_vat_number_${acquirerId}`),
                };
            } else if (flow === 'token') {
                return {
                    code: document.getElementById(`o_token_code_${acquirerId}`),
                };
            }
        },

        _prepareTransactionRouteParams: function (provider, paymentOptionId, flow, token=null) {
            var dict = this._super(...arguments);
            if (token)
                dict['mercadopago_tmp_token'] = token;
            return dict;
        },

        /**
         * Prepare the inline form of MercadoPago for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'mercadopago') {
                return this._super(...arguments);
            }
            this._rpc({
                route: '/payment/mercadopago/get_acquirer_info',
                params: {
                    'rec_id': paymentOptionId,
                    'flow': flow,
                },
            }).then(acquirerInfo => {
                var self = this;
                ajax.loadJS("https://secure.mlstatic.com/sdk/javascript/v1/mercadopago.js").then((mp) => {
                    ajax.loadJS("https://sdk.mercadopago.com/js/v2").then((mp) => {
                        self.mercadopagoInfo = acquirerInfo;
                        // Initialize MercadoPago v1
                        window.Mercadopago.setPublishableKey(acquirerInfo.publishable_key);
                        window.Mercadopago.getIdentificationTypes();
                        // Initialize MercadoPago v2
                        self.mp = new MercadoPago(acquirerInfo.publishable_key);
                        if (flow === 'token') {
                            return Promise.resolve(); // Don't show the form for tokens
                        }
                        else {
                            this._setPaymentFlow('direct');
                            this._MercadoPagoProcessForm(paymentOptionId)
                        }
        

                    });
                });
                

            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occurred when displayed this payment form."),
                    error.message.data.message
                );
            });
        },

        /**
         * Process the form of MercadoPago for direct payment.
         *
         * @private
         * @param {string} publishable_key - MercadoPago public key
         */
        _MercadoPagoProcessForm: function (paymentOptionId) {
            document.getElementById('o_mercadopago_card_number_' + paymentOptionId).addEventListener('change', guessPaymentMethod);

            self = this;
            function guessPaymentMethod(event) {
                let cardnumber = document.getElementById('o_mercadopago_card_number_' + paymentOptionId).value.split(" ").join("");
                if (cardnumber.length >= 6) {
                    let bin = cardnumber.substring(0,6);
                    window.Mercadopago.getPaymentMethod({
                        "bin": bin
                    }, setPaymentMethod);
                }
                let issuerLabel = document.getElementById('o_mercadopago_issuer_label_' + paymentOptionId);
                let issuerSelect = document.getElementById('o_mercadopago_issuer_' + paymentOptionId);
                issuerLabel.classList.add("o_hidden");
                issuerSelect.classList.add("o_hidden");
                let installmentsLabel = document.getElementById('o_mercadopago_installments_label_' + paymentOptionId);
                let installments = document.getElementById('o_mercadopago_installments_' + paymentOptionId);
                installmentsLabel.classList.add("o_hidden");
                installments.classList.add("o_hidden");
            };

            function setPaymentMethod(status, response) {
                if (status == 200) {
                    let paymentMethod = response[0];
                    document.getElementById('o_mercadopago_payment_method_' + paymentOptionId).value = paymentMethod.id;

                    if(paymentMethod.additional_info_needed.includes("issuer_id")){
                        getIssuers(paymentMethod.id);
                    } else {
                        getInstallments(
                            paymentMethod.id,
                            self.txContext.amount,
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
                    let issuerLabel = document.getElementById('o_mercadopago_issuer_label_' + paymentOptionId);
                    let issuerSelect = document.getElementById('o_mercadopago_issuer_' + paymentOptionId);
                    issuerLabel.classList.remove("o_hidden");
                    issuerSelect.classList.remove("o_hidden");
                    response.forEach( issuer => {
                        let opt = document.createElement('option');
                        opt.text = issuer.name;
                        opt.value = issuer.id;
                        issuerSelect.appendChild(opt);
                    });

                    getInstallments(
                        document.getElementById('o_mercadopago_payment_method_' + paymentOptionId).value,
                        self.txContext.amount,
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
                    let installmentsLabel = document.getElementById('o_mercadopago_installments_label_' + paymentOptionId);
                    let installments = document.getElementById('o_mercadopago_installments_' + paymentOptionId);
                    let show_installments = $(installments).data('show');
                    if (show_installments)
                        installmentsLabel.classList.remove("o_hidden");
                        installments.classList.remove("o_hidden");
                    installments.options.length = 0;
                    response[0].payer_costs.forEach( payerCost => {
                        let opt = document.createElement('option');
                        opt.text = payerCost.recommended_message;
                        opt.value = payerCost.installments;
                        installments.appendChild(opt);
                    });
                } else {
                    alert('installments method info error: ${response}');
                }
            };
        },

        /**
         * Dispatch the secure data to Authorize.Net.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (provider, paymentOptionId, flow) {
            if (provider !== 'mercadopago' || flow !== 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }
            return this._processTokenPayment(provider, paymentOptionId, flow);
        },

        /**
         * Dispatch the secure data to MercadoPago.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the acquirer
         * @param {number} paymentOptionId - The id of the acquirer handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        _processDirectPayment: function (provider, paymentOptionId, processingValues) {
            if (provider !== 'mercadopago') {
                return this._super(...arguments);
            }

            if (!this._MercadoPagoValidateFormInputs(paymentOptionId, 'direct')) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve();
            }

            return this._createMercadoPagoToken(paymentOptionId).then((response) => this._MercadoPagoResponseHandler(processingValues, response));
        },

        /**
         * called when clicking on pay now or add payment event to create token for credit card/debit card.
         *
         * @private
         * @param {number} acquirerId - The id of the acquirer handling the transaction
         * @return {Promise}
         */
        _createMercadoPagoToken: function(acquirerId) {
            let form = document.getElementById('o_mercadopago_form_' + acquirerId);
            self = this;
            return new Promise (function(resolve, reject) {
                window.Mercadopago.createToken(form, function setCardToken(status, response) {
                    if (status == 200 || status == 201) {
                        resolve(response);
                    } else {
                        var error_msg = error_messages[response.cause[0].code];
                        if (error_msg === undefined)
                            error_msg = error_messages['0']
                        self._displayError(
                            _t("Server Error"),
                            _t("An error occurred when displayed this payment form."),
                            _t(error_msg));
                    }
                });
            });
        },

        /**
         * Handle the response from MercadoPago and initiate the payment.
         *
         * @private
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        _MercadoPagoResponseHandler: function (processingValues, response) {
            if (!response.id) {
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment.")
                );
                return Promise.resolve();
            }
            // Initiate the payment
            return this._rpc({
                route: '/payment/mercadopago/payment',
                params: {
                    'reference': processingValues.reference,
                    'partner_id': processingValues.partner_id,
                    'access_token': processingValues.access_token,
                    //'acquirer_id': processingValues.acquirer_id,
                    'mercadopago_token': response.id,
                    'mercadopago_payment_method': document.getElementById('o_mercadopago_payment_method_' + processingValues.acquirer_id).value,
                    'installments': parseInt(document.getElementById('o_mercadopago_installments_' + processingValues.acquirer_id).value),
                    'issuer': parseInt(document.getElementById('o_mercadopago_issuer_' + processingValues.acquirer_id).value),
                    'email': document.getElementById('email').value,
                }
            }).then(() => window.location = '/payment/status');
        },

        /**
         * Checks that all payment inputs adhere to the DOM validation constraints.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {boolean} - Whether all elements pass the validation constraints
         */
         _MercadoPagoValidateFormInputs: function (acquirerId, flow) {
            const inputs = Object.values(this._MercadoPagoGetInlineFormInputs(acquirerId, flow));
            return inputs.every(element => element.reportValidity());
        },

        /**
         * Payment form MercadoPago Token.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the acquirer
         * @param {number} paymentOptionId - The id of the acquirer handling the transaction
         * @return {Promise}
         */
        _processTokenPayment(provider, paymentOptionId, flow){
            if (provider !== 'mercadopago') {
                return this._super(...arguments);
            }

            if (!this._MercadoPagoValidateFormInputs(paymentOptionId, 'token')) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve();
            }
            return this._rpc({
                route: "/payment/mercadopago/token",
                params: {
                    'token_id':paymentOptionId
                },
            }).then(response => {
                self = this;
                (async function createToken() {
                    try {
                        const token = await self.mp.createCardToken({
                            cardId: response['card_token'],
                            securityCode: document.getElementById(`o_token_code_${paymentOptionId}`).value,
                        })
                        // Use the received token to make a POST request to your backend
                        return self._rpc({
                            route: self.txContext.transactionRoute,
                            params: self._prepareTransactionRouteParams(provider, paymentOptionId, flow, token.id),
                        }).then(response => {
                            // TODO: check something on processing values before redirect?
                            window.location = '/payment/status'
                        });
                    }catch(e) {
                        console.error('error creating token: ', e)
                    }
                })()
            }).guardedCatch(error => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message
                );
            });

        }
    };

    checkoutForm.include(mercadopagoMixin);
    manageForm.include(mercadopagoMixin);
});
