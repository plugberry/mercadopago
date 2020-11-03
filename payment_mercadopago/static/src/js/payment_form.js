odoo.define('payment_mercadopago.payment_form', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var Dialog = require('web.Dialog');
    var session = require('web.session');
    var _t = core._t;
    var Qweb = core.qweb;


         function guessPaymentMethod(event) {
            let cardnumber = document.getElementById("cardNumber").value;
            if (cardnumber.length >= 6) {
                let bin = cardnumber.substring(0, 7);
                window.Mercadopago.getPaymentMethod({
                    "bin": bin
                }, setPaymentMethod);
            }
        };

        function setPaymentMethod(status, response) {
            if (status == 200) {
                let paymentMethod = response[0];
                document.getElementById('paymentMethodId').value = paymentMethod.id;

                if (paymentMethod.additional_info_needed.includes("issuer_id")) {
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
            if (status == 200) {
                let issuerSelect = document.getElementById('issuer');
                $("#issuerInput").removeClass('d-none');
                response.forEach(issuer => {
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
            }
        };
        function getInstallments(paymentMethodId, transactionAmount, issuerId) {
            window.Mercadopago.getInstallments({
                "payment_method_id": paymentMethodId,
                "amount": parseFloat(transactionAmount),
                "issuer_id": issuerId ? parseInt(issuerId) : undefined
            }, setInstallments);
        };

        function setInstallments(status, response) {
            if (status == 200) {
                document.getElementById('installments').options.length = 0;
                response[0].payer_costs.forEach(payerCost => {
                    let opt = document.createElement('option');
                    opt.text = payerCost.recommended_message;
                    opt.value = payerCost.installments;
                    document.getElementById('installments').appendChild(opt);
                });
            } else {
                alert(`installments method info error: ${response}`);
            }
        };

        function getCardToken(event) {
            event.preventDefault();
            if (!this.doSubmit) {
                let $form = document.getElementById('paymentForm');
                window.Mercadopago.createToken($form, setCardTokenAndPay);
                return false;
            }
        };

        function setCardTokenAndPay( status, response) {
            if (status == 200 || status == 201) {
                let form = document.getElementById('paymentForm');
                let card = document.createElement('input');
                card.setAttribute('name', 'token');
                card.setAttribute('type', 'hidden');
                card.setAttribute('value', response.id);
                form.appendChild(card);
                this.doSubmit = true;
                form.submit();
            } else {
                alert("Verify filled data!\n" + JSON.stringify(response, null, 4));
            }
        };

    var templateLoaded = ajax.loadXML('/payment_mercadopago/static/src/xml/payment_form_mercadopago.xml', Qweb);

    PaymentForm.include({
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
            console.log(session);
            if (ev.type === 'submit') {
                var button = $(ev.target).find('*[type="submit"]')[0]
            } else {
                var button = ev.target;
            }
            this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            var formData = self.getFormData(inputsForm);
            templateLoaded.finally(
                function() {

                    var dialog = new Dialog(null, {
                        title: _t('Adicionando Tarjeta'),
                        size: 'medium',
                        $content: Qweb.render("payment_mercadopago.mercadopago_form_external_payment", {'csrf_toke': core.csrf_token, 'acquired_id': acquirerID}),
                    });window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);
                    dialog.open().opened(
                        function(){
                            window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);
                            window.Mercadopago.getIdentificationTypes();
                            document.getElementById('cardNumber').addEventListener('change', guessPaymentMethod);
                            self.doSubmit = false;
                            document.getElementById('paymentForm').addEventListener('submit', getCardToken);

                            $("#issuerInwindow.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);put").addClass('d-none');
                            $("footer.modal-footer").addClass('d-none');
                            var cardNumber = $('#cardNumber');
                            var cardNumberField = $('#card-number-field');
                            var mastercard = $("#mastercard");
                            var visa = $("#visa");
                            var amex = $("#amex");

                            cardNumber.keyup(function() {
                                amex.removeClass('transparent');
                                visa.removeClass('transparent');
                                mastercard.removeClass('transparent');

                                if ($.payform.validateCardNumber(cardNumber.val()) == false) {
                                    cardNumberField.addClass('has-error');
                                } else {
                                    cardNumberField.removeClass('has-error');
                                    cardNumberField.addClass('has-success');
                                }

                                if ($.payform.parseCardType(cardNumber.val()) == 'visa') {
                                    mastercard.addClass('transparent');
                                    amex.addClass('transparent');
                                } else if ($.payform.parseCardType(cardNumber.val()) == 'amex') {
                                    mastercard.addClass('transparent');
                                    visa.addClass('transparent');
                                } else if ($.payform.parseCardType(cardNumber.val()) == 'mastercard') {
                                    amex.addClass('transparent');
                                    visa.addClass('transparent');
                                }
                            });
                        }
                    );
                    dialog.on('closed', self, function () {
                      this.enableButton(button);
                    });
                });
        },

        updateNewPaymentDisplayStatus: function() {
            var $checkedRadio = this.$('input[type="radio"]:checked');

            if ($checkedRadio.length !== 1) {
                return;
            }

            //  hide add token form for authorize
            if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {
                var script = $('script[src="https://www.mercadopago.com.uy/integrations/v1/web-tokenize-checkout.js"]')
                script.attr('data-transaction-amount', $('#order_total .oe_currency_value').text());
                script.attr('src', 'https://www.mercadopago.com.ar/integrations/v1/web-tokenize-checkout.js');
                var inputs = $('.o_payment_form input')
                inputs.each(
                    function(iter, item) {
                        var newItem = $(item).clone();
                        newItem.addClass('inputhidden');
                        $('.o_payment_mercadopago').append(
                            newItem
                        )
                    }
                )
            } else {
                $('.o_payment_mercadopago input').remove();
            }
            this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        isMercadopagoPayExist: function(element) {
            return $(element).data('mercadopago') === 'True';
        },

        /**
         * @override
         */
        payEvent: function(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var form = this.el;
            var $checkedRadio = this.$('input[type="radio"]:checked');
            var acquirer_id = $checkedRadio.data('acquirer-id');
            var self = this;
            var button = ev.target;
            //
            // first we check that the user has selected a authorize as s2s payment method
            if ($checkedRadio.length === 1) {
                if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {
                    $('.mercadopago-button').click();
                } else if (this.isMercadopagoPayExist($checkedRadio)) {
                    var msg = _t("Just one more second, We are redirecting you to Stripe...");
                    $.blockUI({
                        'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                            '    <br />' + msg +
                            '</h2>'
                    });
                    ajax.jsonRpc(
                        '/payment/existing_card/mercadopago',
                        'call', {
                            token_id: $checkedRadio[0].value,
                            acquirer_id: acquirer_id,
                        }
                    ).then(function(data) {
                        // if the server has returned true
                        if (data.result) {
                            $.unblockUI();
                            checked_radio.value = data.id; // set the radio value to the new card id
                            form.submit();
                            return $.Deferred();
                        }
                        // if the server has returned false, we display an error
                        else {
                            $.unblockUI();
                            if (data.error) {
                                self.displayError(
                                    '',
                                    data.error);
                            } else { // if the server doesn't provide an error message
                                self.displayError(
                                    _t('Server Error'),
                                    _t('e.g. Your credit card details are wrong. Please verify.'));
                            }
                        }
                        // here we remove the 'processing' icon from the 'add a new payment' button
                        $(button).attr('disabled', false);
                        $(button).children('.fa').addClass('fa-plus-circle')
                        $(button).find('span.o_loader').remove();
                        $.unblockUI();
                    });
                } else {
                    this._super.apply(this, arguments);
                }
            } else {
                self.displayError(
                    _t('No payment method selected'),
                    _t('Please select a payment method.')
                );
            }

            // this._super.apply(this, arguments);
        },
        /**
         * @override
         */
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

        displayError: function(title, message) {
            var $checkedRadio = this.$('input[type="radio"][name="pm_id"]:checked'),
                acquirerID = this.getAcquirerIdFromRadio($checkedRadio[0]);
            var $acquirerForm;
            if (this.isNewPaymentRadio($checkedRadio[0])) {
                $acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            } else if (this.isFormPaymentRadio($checkedRadio[0])) {
                $acquirerForm = this.$('#o_payment_form_acq_' + acquirerID);
            } else if (this.isMercadopagoPayExist($checkedRadio[0])) {
                return new Dialog(null, {
                    title: _t('Error: ') + _.str.escapeHTML(title),
                    size: 'medium',
                    $content: "<p>" + (_.str.escapeHTML(message) || "") + "</p>",
                    buttons: [{
                        text: _t('Ok'),
                        close: true
                    }]
                }).open();
            }

            if ($checkedRadio.length === 0) {
                return new Dialog(null, {
                    title: _t('Error: ') + _.str.escapeHTML(title),
                    size: 'medium',
                    $content: "<p>" + (_.str.escapeHTML(message) || "") + "</p>",
                    buttons: [{
                        text: _t('Ok'),
                        close: true
                    }]
                }).open();
            } else {
                // removed if exist error message
                this.$('#payment_error').remove();
                var messageResult = '<div class="alert alert-danger mb4" id="payment_error">';
                if (title != '') {
                    messageResult = messageResult + '<b>' + _.str.escapeHTML(title) + ':</b></br>';
                }
                messageResult = messageResult + _.str.escapeHTML(message) + '</div>';
                $acquirerForm.append(messageResult);
            }
        },
    });
});
