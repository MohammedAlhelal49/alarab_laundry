from . import models

def _set_report_layout(env):
    company = env['res.company'].search([], limit=1)
    layout = env.ref('web.external_layout_striped', raise_if_not_found=False)
    if company and layout:
        company.external_report_layout_id = layout.id