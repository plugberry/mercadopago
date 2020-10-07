odoo.define('payment_mercadopago.payment_form', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var PaymentForm = require('payment.payment_form');

var _t = core._t;







PaymentForm.include({

    // willStart: function () {
    //     return this._super.apply(this, arguments).then(function () {
    //         return ajax.loadJS("https://www.mercadopago.com.ar/integrations/v1/web-tokenize-checkout.js");
    //     })
    // },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    guessPaymentMethod: function(event) {
       let cardnumber = document.getElementById("cardNumber").value;
       if (cardnumber.length >= 6) {
           let bin = cardnumber.substring(0,6);
           window.Mercadopago.getPaymentMethod({
               "bin": bin
           }, this.setPaymentMethod);
       }
    },

    setPaymentMethod: function(status, response) {
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
    },

    /**
     * called when clicking on pay now or add payment event to create token for credit card/debit card.
     *
     * @private
     * @param {Event} ev
     * @param {DOMElement} checkedRadio
     * @param {Boolean} addPmEvent
     */
    // _createMercadoPagoToken: function (ev, $checkedRadio, addPmEvent) {
    //     var self = this;
    //     if (ev.type === 'submit') {
    //         var button = $(ev.target).find('*[type="submit"]')[0]
    //     } else {
    //         var button = ev.target;
    //     }
    //     this.disableButton(button);
    //     var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
    //     var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
    //     var inputsForm = $('input', acquirerForm);
    //     var formData = self.getFormData(inputsForm);
    //     if (this.options.partnerId === undefined) {
    //         console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
    //     }
    //     var AcceptJs = false;
    //     if (formData.acquirer_state === 'enabled') {
    //         AcceptJs = 'https://www.mercadopago.com.ar/integrations/v1/web-tokenize-checkout.js';
    //     } else {
    //         AcceptJs = 'https://www.mercadopago.com.ar/integrations/v1/web-tokenize-checkout.js';
    //     }
    //
    //     window.responseHandler = function (response) {
    //         _.extend(formData, response);
    //
    //         if (response.messages.resultCode === "Error") {
    //             var errorMessage = "";
    //             _.each(response.messages.message, function (message) {
    //                 errorMessage += message.code + ": " + message.text;
    //             })
    //             acquirerForm.removeClass('d-none');
    //             self.enableButton(button);
    //             return self.displayError(_t('Server Error'), errorMessage);
    //         }
    //
    //         self._rpc({
    //             route: formData.data_set,
    //             params: formData
    //         }).then (function (data) {
    //             if (addPmEvent) {
    //                 if (formData.return_url) {
    //                     window.location = formData.return_url;
    //                 } else {
    //                     window.location.reload();
    //                 }
    //             } else {
    //                 $checkedRadio.val(data.id);
    //                 self.el.submit();
    //             }
    //         }).guardedCatch(function (error) {
    //             // if the rpc fails, pretty obvious
    //             error.event.preventDefault();
    //             acquirerForm.removeClass('d-none');
    //             self.enableButton(button);
    //             self.displayError(
    //                 _t('Server Error'),
    //                 _t("We are not able to add your payment method at the moment.") +
    //                     self._parseError(error)
    //             );
    //         });
    //     };
    //
    //     if (this.$button === undefined) {
    //         var params = {
    //             class: 'AcceptUI d-none',
    //             // data-public-key: formData.mercadopago_publishable_key,
    //             // data-transaction-amount: 200,
    //         };
    //         this.$button = $('<button>', params);
    //         this.$button.appendTo('body');
    //     }
    //     ajax.loadJS(AcceptJs).then(function () {
    //         self.$button.trigger('click');
    //     });
    // },
    /**
     * @override
     */
    updateNewPaymentDisplayStatus: function () {
        var $checkedRadio = this.$('input[type="radio"]:checked');

        if ($checkedRadio.length !== 1) {
            return;
        }

        //  hide add token form for authorize
        if ($checkedRadio.data('provider') === 'mercadopago' && this.isNewPaymentRadio($checkedRadio)) {
            // this.$('[id*="o_payment_add_token_acq_"]').addClass('d-none');
            var script = $('script[src="https://www.mercadopago.com.uy/integrations/v1/web-tokenize-checkout.js"]')
            script.attr('data-transaction-amount', $('#order_total .oe_currency_value').text());
            var inputs = $('.o_payment_form input')
            inputs.each(
                function(iter, item){
                    var newItem = $(item).clone();
                    newItem.addClass('inputhidden');
                    $('.o_payment_mercadopago').append(
                        newItem
                    )
                }
            )
            // window.Mercadopago.setPublishableKey("TEST-6cb31e18-4db7-45c5-8035-d8b20a2d899e");
            // document.getElementById('cardNumber').addEventListener('change', this.guessPaymentMethod);
        }
        else{
            $('.o_payment_mercadopago input').remove();
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
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');
        //
        // first we check that the user has selected a authorize as s2s payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
            // this._createMercadoPagoToken(ev, $checkedRadio);
            $('.mercadopago-button').click();
        }
        else{
            this._super.apply(this, arguments);
        }
        // this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    addPmEvent: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var $checkedRadio = this.$('input[type="radio"]:checked');

        // first we check that the user has selected a authorize as add payment method
        if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'mercadopago') {
            // this._createMercadoPagoToken(ev, $checkedRadio, true);
            $('.mercadopago-button').click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
