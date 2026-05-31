from odoo import fields, models


class InsurancePolicyTerm(models.Model):
    _inherit = "insurance.policy.term"

    agent_id = fields.Many2one(
        "insurance.agent",
        ondelete="restrict",
        string="Agente",
    )
