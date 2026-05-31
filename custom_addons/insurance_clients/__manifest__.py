{
    "name": "Insurance Clients",
    "version": "19.0.3.0.0",
    "category": "Insurance",
    "summary": "Insurance client profiles linked to Odoo contacts.",
    "author": "Techbros",
    "license": "LGPL-3",
    "depends": ["insurance_base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/insurance_clients_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "insurance_clients/static/src/xml/form_status_indicator.xml",
        ],
    },
    "application": False,
    "installable": True,
}
