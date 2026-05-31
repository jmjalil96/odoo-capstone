from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InsurancePartnerProfileMixin(models.AbstractModel):
    _name = "insurance.partner.profile.mixin"
    _description = "Insurance Partner Profile Mixin"

    # Partner fields copied onto the linked res.partner when a profile is
    # created without an existing partner. Subclasses may extend this list.
    _partner_value_fields = [
        "vat",
        "phone",
        "email",
        "street",
        "street2",
        "city",
        "state_id",
        "country_id",
    ]
    # Fallback partner name when no usable name/vat is provided. Overridden per model.
    _partner_default_name = "Perfil de seguros"
    # Message raised when an active duplicate VAT is detected. Overridden per model.
    _vat_duplicate_message = "Ya existe un perfil de seguros con este numero de identificacion."

    active = fields.Boolean(default=True)
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        index=True,
        string="Contacto",
    )
    name = fields.Char(related="partner_id.name", readonly=False, store=True, string="Nombre")
    vat = fields.Char(
        related="partner_id.vat",
        readonly=False,
        store=True,
        index=True,
        string="Numero de identificacion",
    )
    phone = fields.Char(related="partner_id.phone", readonly=False, store=True, string="Celular")
    email = fields.Char(related="partner_id.email", readonly=False, store=True, string="Correo")
    street = fields.Char(related="partner_id.street", readonly=False, store=True, string="Direccion")
    street2 = fields.Char(related="partner_id.street2", readonly=False, store=True, string="Direccion 2")
    city = fields.Char(related="partner_id.city", readonly=False, store=True, string="Ciudad")
    state_id = fields.Many2one(
        "res.country.state",
        related="partner_id.state_id",
        readonly=False,
        store=True,
        string="Provincia",
    )
    country_id = fields.Many2one(
        "res.country",
        related="partner_id.country_id",
        readonly=False,
        store=True,
        string="Pais",
    )
    is_company = fields.Boolean(
        related="partner_id.is_company",
        readonly=False,
        store=True,
        string="Es compania",
    )

    @api.depends("is_company")
    def _compute_company_type(self):
        for record in self:
            record.company_type = "company" if record.is_company else "person"

    def _inverse_company_type(self):
        for record in self:
            record.is_company = record.company_type == "company"

    @api.model
    def _is_company_from_vals(self, vals):
        if "is_company" in vals:
            return vals["is_company"]
        if vals.get("company_type"):
            return vals["company_type"] == "company"
        return False

    @api.model
    def _vat_from_create_vals(self, vals):
        if "vat" in vals:
            return vals["vat"]
        if vals.get("partner_id"):
            return self.env["res.partner"].browse(vals["partner_id"]).vat
        return False

    @api.model
    def _raise_if_duplicate_vat(self, vat, excluded_ids=None):
        if not vat:
            return
        domain = [
            ("active", "=", True),
            ("vat", "=", vat),
        ]
        if excluded_ids:
            domain.append(("id", "not in", excluded_ids))
        if self.search(domain, limit=1):
            raise ValidationError(self._vat_duplicate_message)

    def _partner_name_from_vals(self, vals):
        return vals.get("name") or vals.get("vat") or self._partner_default_name

    def _prepare_partner_vals(self, vals):
        partner_vals = {
            "type": "contact",
            "is_company": self._is_company_from_vals(vals),
            "name": self._partner_name_from_vals(vals),
        }
        for field_name in self._partner_value_fields:
            if field_name in vals:
                partner_vals[field_name] = vals[field_name]
        return partner_vals

    def _prepare_profile_vals(self, vals):
        """Hook to normalize a single create vals dict before partner creation."""
        return vals

    def _prepare_write_vals(self, vals):
        """Hook to normalize write vals before delegating to super().write()."""
        return vals

    def _post_create_profile(self):
        """Hook run on freshly created profiles."""
        return

    def _post_write_profile(self, vals):
        """Hook run after a successful write, receiving the prepared vals."""
        return

    @api.model
    def _check_duplicate_vats_on_create(self, vals_list):
        seen_vats = set()
        for vals in vals_list:
            if vals.get("active", True):
                vat = self._vat_from_create_vals(vals)
                if vat in seen_vats:
                    raise ValidationError(self._vat_duplicate_message)
                self._raise_if_duplicate_vat(vat)
                if vat:
                    seen_vats.add(vat)

    def _check_duplicate_vats_on_write(self, vals):
        if {"active", "vat"}.intersection(vals):
            for record in self:
                active = vals.get("active", record.active)
                vat = vals.get("vat", record.vat)
                if active:
                    record._raise_if_duplicate_vat(vat, excluded_ids=record.ids)

    @api.model_create_multi
    def create(self, vals_list):
        self._check_duplicate_vats_on_create(vals_list)

        prepared_vals = []
        for vals in vals_list:
            vals = self._prepare_profile_vals(dict(vals))
            if not vals.get("partner_id"):
                partner = self.env["res.partner"].create(self._prepare_partner_vals(vals))
                vals["partner_id"] = partner.id
                vals.setdefault("name", partner.name)
            prepared_vals.append(vals)
        records = super().create(prepared_vals)
        records._post_create_profile()
        return records

    def write(self, vals):
        self._check_duplicate_vats_on_write(vals)
        vals = self._prepare_write_vals(vals)
        result = super().write(vals)
        self._post_write_profile(vals)
        return result

    @api.constrains("active", "vat")
    def _check_vat_unique(self):
        for record in self:
            if not record.active or not record.vat:
                continue
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("active", "=", True),
                    ("vat", "=", record.vat),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(self._vat_duplicate_message)
