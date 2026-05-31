from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InsuranceClient(models.Model):
    _name = "insurance.client"
    _description = "Insurance Client"
    _inherit = ["insurance.partner.profile.mixin"]
    _rec_name = "name"
    _order = "name"

    _partner_value_fields = [
        "vat",
        "phone",
        "email",
        "street",
        "street2",
        "city",
        "state_id",
        "country_id",
        "user_id",
    ]
    _partner_default_name = "Cliente de seguros"
    _vat_duplicate_message = "Ya existe un cliente de seguros con este numero de identificacion."

    user_id = fields.Many2one(
        "res.users",
        related="partner_id.user_id",
        readonly=False,
        store=True,
        string="Asesor",
    )
    child_ids = fields.One2many(
        related="partner_id.child_ids",
        readonly=False,
        string="Contactos y direcciones",
    )
    company_type = fields.Selection(
        [
            ("person", "Individual"),
            ("company", "Corporativo"),
        ],
        compute="_compute_company_type",
        inverse="_inverse_company_type",
        readonly=False,
        string="Tipo de cliente",
    )

    first_name = fields.Char(string="Nombres", index=True)
    last_name = fields.Char(string="Apellidos", index=True)
    id_type = fields.Selection(
        [
            ("cedula", "Cedula"),
            ("passport", "Pasaporte"),
            ("ruc_natural", "RUC persona natural"),
            ("ruc_juridica", "RUC persona juridica"),
        ],
        string="Tipo de identificacion",
        index=True,
    )
    gender = fields.Selection(
        [
            ("male", "Masculino"),
            ("female", "Femenino"),
        ],
        string="Sexo",
    )
    birthdate = fields.Date(string="Fecha de nacimiento")
    occupation = fields.Char(string="Ocupacion")
    activity = fields.Char(string="Actividad")

    _partner_unique = models.Constraint(
        "UNIQUE(partner_id)",
        "Este contacto ya tiene un perfil de cliente de seguros.",
    )

    def init(self):
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS insurance_client_vat_active_unique
                ON insurance_client (vat)
             WHERE active IS TRUE
               AND vat IS NOT NULL
               AND vat != ''
            """
        )

    @api.model
    def _display_name_from_parts(self, first_name=None, last_name=None, id_number=None):
        person_name = " ".join(part for part in [first_name, last_name] if part)
        return person_name or id_number

    def _partner_name_from_vals(self, vals):
        if self._is_company_from_vals(vals):
            name = vals.get("name")
        else:
            name = self._display_name_from_parts(
                vals.get("first_name"),
                vals.get("last_name"),
                vals.get("vat"),
            )
        return name or vals.get("vat") or self._partner_default_name

    def _post_create_profile(self):
        self._sync_individual_display_name()

    def _post_write_profile(self, vals):
        if self.env.context.get("skip_insurance_client_name_sync"):
            return
        sync_fields = {"first_name", "last_name", "vat", "is_company", "company_type"}
        if sync_fields.intersection(vals):
            self._sync_individual_display_name()

    def _sync_individual_display_name(self):
        for client in self:
            if client.is_company:
                continue
            display_name = client._display_name_from_parts(
                client.first_name,
                client.last_name,
                client.vat,
            )
            if display_name and client.name != display_name:
                client.with_context(skip_insurance_client_name_sync=True).write({"name": display_name})

    @api.constrains("is_company", "first_name", "last_name", "id_type", "vat", "name")
    def _check_required_fields(self):
        for client in self:
            if not client.vat:
                raise ValidationError("El numero de identificacion es obligatorio para clientes de seguros.")
            if not client.id_type:
                raise ValidationError("El tipo de identificacion es obligatorio para clientes de seguros.")
            if client.is_company:
                if not client.name:
                    raise ValidationError("La razon social es obligatoria para clientes corporativos.")
            elif not client.first_name or not client.last_name:
                raise ValidationError("Nombres y apellidos son obligatorios para clientes individuales.")
