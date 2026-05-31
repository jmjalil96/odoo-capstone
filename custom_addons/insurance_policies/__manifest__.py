{
    "name": "Insurance Policies",
    "version": "19.0.3.0.0",
    "category": "Insurance",
    "summary": "Bare-bones insurance policies linked to insurance clients.",
    "author": "Techbros",
    "license": "LGPL-3",
    "depends": ["insurance_clients"],
    "data": [
        "security/ir.model.access.csv",
        "views/insurance_policy_views.xml",
    ],
    "demo": [
        "demo/insurance_policies_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "insurance_policies/static/src/xml/form_status_indicator.xml",
        ],
    },
    "application": False,
    "installable": True,
}
