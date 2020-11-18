odoo.define('payment_mercadopago.payment_form', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var Dialog = require('web.Dialog');
    var session = require('web.session');
    var _t = core._t;
    var Qweb = core.qweb;
    var ERRORS = {
        '205': 'El número de la tarjeta de no puede esta vacío. \n' +
        'Introduzca un número de tarjeta.',
        '208': 'El mes de la fecha de vencimiento no puede esta vacío. \n' +
        'Introduzca un mes.',
        '209': 'El año de la fecha de vencimiento no puede esta vacío. \n' +
        'Introduzca un año.',
        '212': 'El tipo de documento no puede estar vacío. \n' +
        'Introduzca un número de documento.',
        '214': 'El número de documento no puede estar vacío. \n' +
        'Introduzca el número de documento.',
        '221': 'El titular de la tarjeta no puede estra vacío. \n' +
        'Introduzca el titular de la tarjeta.',
        '224': 'El código de seguridad no puede estar vacío. \n' +
        'Introduzca el código de seguridad.',
        'E301': 'Inválido número de tarjeta. \n' +
        'Revise el número de tarjeta.',
        'E302': 'Inválido código de seguridad. \n' +
        'Revise el código de seguridad.',
        '316': 'Inválido titular de la tarjeta.\n' +
        'Introduzca un titular correcto.',
        '322': 'Inválido tipo de documento.',
        '324': 'Inválido número de documento.',
        '325': 'Inválido parámetro de mes de fecha de vencimiento.',
        '326': 'Inválido parámetro de año de fecha de vencimiento.',
        '400': 'Código de seguridad incorrecto'
    }

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
            if (response.cause){
                var msg = ERRORS[response.cause[0].code]
                alert("Verifique algunos datos del formulario!\n" + msg)
            }
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
            // this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            this.acquirerID = acquirerID
            ajax.jsonRpc('/acquirer_amount',
                'call',
                {
                    acquirer_id:acquirerID
                }).then(function(data){
                    var acquirerForm = self.$('#o_payment_add_token_acq_' + self.acquirerID);
                    var inputsForm = $('input', acquirerForm);
                    var formData = self.getFormData(inputsForm);
                    templateLoaded.finally(
                        function() {
                            var dialog = new Dialog(null, {
                                title: _t('Adicionando Tarjeta'),
                                size: 'medium',
                                $content: Qweb.render("payment_mercadopago.mercadopago_form_external_payment",
                                    {
                                        'acquired_id': acquirerID,
                                        'mercadopago_authorize_amount': data.mercadopago_authorize_amount,
                                        'mpm':1
                                    }),
                            });
                            dialog.open().opened(
                                function(){
                                    window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);
                                    window.Mercadopago.getIdentificationTypes();
                                    document.getElementById('cardNumber').addEventListener('change', guessPaymentMethod);
                                    self.doSubmit = false;
                                    document.getElementById('paymentForm').addEventListener('submit', getCardToken);

                                    $("#issuerInput").addClass('d-none');
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
                        }
                    );
                }
            );
        },

        // updateNewPaymentDisplayStatus: function() {
        //     var $checkedRadio = this.$('input[type="radio"]:checked');
        //
        //     if ($checkedRadio.length !== 1) {
        //         return;
        //     }
        //
        //     if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {
        //         var script = $('script[src="https://www.mercadopago.com.uy/integrations/v1/web-tokenize-checkout.js"]')
        //         script.attr('data-transaction-amount', $('#order_total .oe_currency_value').text());
        //         script.attr('src', 'https://www.mercadopago.com.ar/integrations/v1/web-tokenize-checkout.js');
        //         var inputs = $('.o_payment_form input')
        //         inputs.each(
        //             function(iter, item) {
        //                 var newItem = $(item).clone();
        //                 newItem.addClass('inputhidden');
        //                 $('.o_payment_mercadopago').append(
        //                     newItem
        //                 )
        //             }
        //         )
        //     } else {
        //         $('.o_payment_mercadopago input').remove();
        //     }
        //     this._super.apply(this, arguments);
        // },

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
            var self = this;
            var button = ev.target;

            if ($checkedRadio.length === 1) {
                if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {

                    var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
                    var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
                    var inputsForm = $('input', acquirerForm);
                    var formData = self.getFormData(inputsForm);
                    templateLoaded.finally(
                    function() {
                        var dialog = new Dialog(null, {
                            title: _t('Adicionando Tarjeta'),
                            size: 'medium',
                            $content: Qweb.render("payment_mercadopago.mercadopago_form_external_payment",
                                {
                                    'acquired_id': acquirerID,
                                    'mercadopago_authorize_amount':0,
                                    'mpm':0
                                }),
                        });
                        dialog.open().opened(
                            function(){
                                window.Mercadopago.setPublishableKey(formData.mercadopago_publishable_key);
                                window.Mercadopago.getIdentificationTypes();
                                document.getElementById('cardNumber').addEventListener('change', guessPaymentMethod);
                                self.doSubmit = false;
                                document.getElementById('paymentForm').addEventListener('submit', getCardToken);

                                $("#issuerInput").addClass('d-none');
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
                } else if (this.isMercadopagoPayExist($checkedRadio)) {
                    $.blockUI();
                    var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
                    var card_id = $checkedRadio.data('card_id');
                    var token_id = $checkedRadio.val();
                    ajax.jsonRpc('/get_cvv',
                        'call',
                        {
                            acquirer_id: acquirerID,
                            card_id:card_id
                        }).then(function(data) {
                            let $form = $(
                                "<form>" +
                                    "<li>" +
                                        "<select id=\"cardId\" name=\"cardId\" data-checkout='cardId'>" +
                                        "<option value=\""+ card_id +"\">" +
                                        "</select>" +
                                    "</li>" +
                                    "<li id=\"cvv\">" +
                                        "<input type=\"text\" id=\"cvv\" data-checkout=\"securityCode\" value=\"" + data.cvv +"\" />" +
                                    "</li>"  +
                                "</form>");
                            window.Mercadopago.setPublishableKey(data.mercadopago_publishable_key);
                                    window.Mercadopago.getIdentificationTypes();
                            window.Mercadopago.createToken($form, function (status, response)
                            {
                                 if (status == 200 || status == 201) {
                                     var token = response.id;
                                     ajax.jsonRpc(
                                         '/payment/existing_card/mercadopago',
                                         'call', {
                                             token: token,
                                             token_id: token_id,
                                             acquirer_id: acquirerID,
                                         }
                                     ).then(function (data) {
                                        // if the server has returned true
                                        if (data.result) {
                                            $.unblockUI();
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
                                 }
                                 else {
                                     if (response.cause) {
                                         var msg = ERRORS[response.cause[0].code]
                                         alert("Verifique algunos datos del formulario!\n" + msg)
                                     }
                                 }
                            });
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
