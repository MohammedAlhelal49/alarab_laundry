def disable_pdc_followup_feature(env):
    """
    Disable PDC Follow-up feature after module installation
    """

    # disable feature flag
    env['ir.config_parameter'].sudo().set_param(
        'sh_pdc_followup.enable_pdc_followup', False
    )

    # disable menu
    menu = env.ref('sh_pdc_followup.pdc_followup_menu', raise_if_not_found=False)
    if menu:
        menu.active = False
