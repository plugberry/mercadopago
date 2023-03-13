##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import controllers
<<<<<<< HEAD
from odoo.addons.payment import reset_payment_acquirer
||||||| parent of bbe24ce (temp)
from odoo.addons.payment.models.payment_acquirer import create_missing_journal_for_acquirers
from odoo.addons.payment import reset_payment_provider
=======
from . import wizards
from odoo.addons.payment.models.payment_acquirer import create_missing_journal_for_acquirers
from odoo.addons.payment import reset_payment_provider
>>>>>>> bbe24ce (temp)


def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'mercadopago')
