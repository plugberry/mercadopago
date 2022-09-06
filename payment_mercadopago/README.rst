.. |company| replace:: Axadoo

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Mercadopago Payment
===================

Mercado pago is the largest online payment platform in Latam.
This module integrates a checkout form and allows you to make payments through this payment gateway. 
Supports automated payments without CVV for subscriptions and card authorizations.

1- Online payment with embedded credit card form (single environment)

2- Payment Status Tracking

3- Recurring payments (Subscriptions)

4- Save Cards



Configuration
=============
To use this module, you need to:

#. Go on to config / payment / payment methods / mercadopago
#. If you want to use it on sales order you should set "validation" to "automatic" (or you can create to payment adquires). The issue is that with "automatic", on payment return with status "pending", no message is displayed to the user regarding pending payment. (still not working)

Get APP and TEST: Credentials: https://www.mercadopago.com.ar/developers/es/docs/resources-faqs/credentials

If we want to process a transaction without CVV, such as collecting a recurring payment, MercadoPago has to authorize credentials.

Test

Test Cards : https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/test-cards



Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/plugberry/mercadopago/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.plugberry.com.
