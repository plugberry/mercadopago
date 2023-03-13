##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import controllers
from . import wizards
from odoo.addons.payment.models.payment_acquirer import create_missing_journal_for_acquirers
from odoo.addons.payment import reset_payment_provider


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'mercadopago')
