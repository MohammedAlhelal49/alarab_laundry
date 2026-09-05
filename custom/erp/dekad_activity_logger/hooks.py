from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Set default tracked models after installation."""
    default_tracked_models = [
        'sale.order', 'sale.order.line',
        'purchase.order', 'purchase.order.line',
        'stock.picking', 'stock.move', 'stock.move.line',
        'res.partner', 'res.users',
        'product.product', 'product.category', 'product.template',
        'pos.order','pdc.wizard', 'res.company',
        'account.move', 'account.move.line', 'account.account', 'account.payment',
        'crm.lead','hr.expense','hr.expense.sheet',
    ]

    # Search for these models in the current database
    # This automatically ignores modules that aren't installed
    models = env['ir.model'].search([('model', 'in', default_tracked_models)])

    if models:
        models.write({'is_activity_tracked': True})
        # Clear the cache so the logger starts working immediately
        env['base']._clear_tracked_models_cache()