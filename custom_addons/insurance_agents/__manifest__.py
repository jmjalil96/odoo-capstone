{
    "name": "Insurance Agents",
    "version": "19.0.3.0.0",
    "category": "Insurance",
    "summary": "Insurance agent profiles and agent contacts.",
    "author": "Techbros",
    "license": "LGPL-3",
    "depends": ["insurance_policies"],
    "data": [
        "security/ir.model.access.csv",
        "views/insurance_agent_views.xml",
        "views/insurance_policy_term_views.xml",
    ],
    "demo": [
        "demo/insurance_agents_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "insurance_agents/static/src/xml/form_status_indicator.xml",
        ],
    },
    "application": False,
    "installable": True,
}
