# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """ One-time data fix, run automatically on every install of this
    module: auto-fill `company_visibility_id` on every product.template
    based on the main company (res.users.company_id) of the user who
    created it (create_uid).

    This heuristic is only safe because, in this deployment, every user
    belongs to exactly one company (no user has access to more than one
    company - confirmed with the client). If that assumption ever
    changes, `create_uid.company_id` may no longer reliably reflect the
    company the product was actually meant for.

    Existing `company_visibility_id` values are never overwritten - this
    only fills products where the field is still empty, so re-running it
    (e.g. on every reinstall during development) is idempotent and never
    clobbers a value that was already set manually or by a previous run.

    After that, `company_visibility_ids` (the Many2many field that
    actually drives visibility) is seeded from `company_visibility_id`
    for every product where the M2M is still empty - same idempotency
    guarantee (never overwrites an already-populated M2M).
    """
    _logger.info("dekad_product_company_visibility: Starting post_init_hook...")

    Product = env['product.template'].with_context(active_test=False)
    products = Product.search([('company_visibility_id', '=', False)])

    updated_count = 0
    skipped_products = []

    for product in products:
        creator = product.create_uid
        if not creator or not creator.company_id:
            skipped_products.append(product)
            continue
        if  product.company_id:
            product.company_visibility_id = product.company_id.id
            updated_count += 1
        elif  creator and creator.company_id :
            product.company_visibility_id = creator.company_id.id
            updated_count += 1

    _logger.info(
        "dekad_product_company_visibility post_init_hook: "
        "assigned company_visibility_id on %s product(s) based on their "
        "creator's company; %s product(s) skipped (no creator or "
        "creator has no main company set).",
        updated_count, len(skipped_products),
    )
    if skipped_products:
        _logger.info(
            "dekad_product_company_visibility post_init_hook: skipped products detail:\n%s",
            "\n".join(
                f"  - [{p.id}] {p.name!r} | create_uid: "
                f"{p.create_uid.name if p.create_uid else 'NONE'}"
                for p in skipped_products
            ),
        )

    # --------------------------------------------------------------
    # Seed company_visibility_ids (Many2many) from company_visibility_id
    # (Many2one) for EVERY product where the legacy field has a value
    # but the new M2M field is still empty - covers both the products
    # just updated above AND any product that already had
    # company_visibility_id set manually/by a previous run, before the
    # M2M field existed.
    # --------------------------------------------------------------
    to_seed = Product.search([
        ('company_visibility_id', '!=', False),
        ('company_visibility_ids', '=', False),
    ])
    for product in to_seed:
        product.company_visibility_ids = [(6, 0, [product.company_visibility_id.id])]

    _logger.info(
        "dekad_product_company_visibility post_init_hook: "
        "seeded company_visibility_ids on %s product(s) from their "
        "existing company_visibility_id value.",
        len(to_seed),
    )
