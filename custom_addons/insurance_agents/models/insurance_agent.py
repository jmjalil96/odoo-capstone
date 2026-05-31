from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InsuranceAgent(models.Model):
    _name = "insurance.agent"
    _description = "Insurance Agent"
    _inherit = ["insurance.partner.profile.mixin"]
    _rec_name = "name"
    _order = "name"

    _partner_default_name = "Agente de seguros"
    _vat_duplicate_message = "Ya existe un agente de seguros con este RUC."

    name = fields.Char(string="Nombre / Razon social")
    vat = fields.Char(string="RUC")
    email = fields.Char(string="Correo electronico")
    company_type = fields.Selection(
        [
            ("person", "Individual"),
            ("company", "Compania"),
        ],
        compute="_compute_company_type",
        inverse="_inverse_company_type",
        readonly=False,
        string="Tipo de agente",
    )
    contact_ids = fields.One2many(
        "insurance.agent.contact",
        "agent_id",
        string="Contactos",
    )

    birthdate = fields.Date(string="Fecha de nacimiento")
    has_credential = fields.Boolean(string="Credencial")
    credential_number = fields.Char(string="Numero de credencial")

    _partner_unique = models.Constraint(
        "UNIQUE(partner_id)",
        "Este contacto ya tiene un perfil de agente de seguros.",
    )

    def init(self):
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS insurance_agent_vat_active_unique
                ON insurance_agent (vat)
             WHERE active IS TRUE
               AND vat IS NOT NULL
               AND vat != ''
            """
        )

    @api.onchange("has_credential")
    def _onchange_has_credential(self):
        for agent in self:
            if not agent.has_credential:
                agent.credential_number = False

    def _prepare_profile_vals(self, vals):
        if not vals.get("has_credential"):
            vals["credential_number"] = False
        return vals

    def _prepare_write_vals(self, vals):
        vals = dict(vals)
        if "has_credential" in vals and not vals["has_credential"]:
            vals["credential_number"] = False
        return vals

    @api.constrains("name", "vat", "has_credential", "credential_number")
    def _check_required_fields(self):
        for agent in self:
            if not agent.name:
                raise ValidationError("El nombre o razon social es obligatorio para agentes de seguros.")
            if not agent.vat:
                raise ValidationError("El RUC es obligatorio para agentes de seguros.")
            if agent.has_credential and not agent.credential_number:
                raise ValidationError("El numero de credencial es obligatorio para agentes con credencial.")
            if not agent.has_credential and agent.credential_number:
                raise ValidationError("Solo los agentes con credencial pueden tener numero de credencial.")


class InsuranceAgentContact(models.Model):
    _name = "insurance.agent.contact"
    _description = "Insurance Agent Contact"
    _rec_name = "name"
    _order = "name"

    agent_id = fields.Many2one(
        "insurance.agent",
        required=True,
        ondelete="cascade",
        index=True,
        string="Agente",
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        index=True,
        string="Contacto",
    )
    name = fields.Char(related="partner_id.name", readonly=False, store=True, string="Nombre")
    function = fields.Char(related="partner_id.function", readonly=False, store=True, string="Cargo")
    email = fields.Char(related="partner_id.email", readonly=False, store=True, string="Correo electronico")
    phone = fields.Char(related="partner_id.phone", readonly=False, store=True, string="Celular")
    birthdate = fields.Date(string="Fecha de nacimiento")

    _agent_partner_unique = models.Constraint(
        "UNIQUE(agent_id, partner_id)",
        "Este contacto ya esta vinculado a este agente.",
    )

    @api.model
    def _partner_vals_from_contact_vals(self, vals):
        agent = self.env["insurance.agent"].browse(vals.get("agent_id"))
        partner_vals = {
            "type": "contact",
            "parent_id": agent.partner_id.id if agent else False,
            "name": vals.get("name") or "Contacto de agente",
        }
        for field_name in ["function", "email", "phone"]:
            if field_name in vals:
                partner_vals[field_name] = vals[field_name]
        return partner_vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if not vals.get("partner_id"):
                partner = self.env["res.partner"].create(self._partner_vals_from_contact_vals(vals))
                vals["partner_id"] = partner.id
                vals.setdefault("name", partner.name)
            prepared_vals.append(vals)
        return super().create(prepared_vals)

    def write(self, vals):
        result = super().write(vals)
        if "agent_id" in vals:
            for contact in self:
                if contact.partner_id.parent_id != contact.agent_id.partner_id:
                    contact.partner_id.parent_id = contact.agent_id.partner_id
        return result
