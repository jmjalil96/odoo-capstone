from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InsurancePolicy(models.Model):
    _name = "insurance.policy"
    _description = "Insurance Policy"
    _rec_name = "policy_number"
    _order = "policy_number"

    area = fields.Selection(
        [
            ("general", "Seguros generales"),
            ("personas", "Personas"),
            ("fianzas", "Fianzas"),
        ],
        required=True,
        string="Area",
    )
    ramo = fields.Selection(
        [
            ("vehiculos", "Vehiculos"),
            ("salud", "Salud"),
            ("vida", "Vida"),
            ("hogar", "Hogar"),
            ("responsabilidad_civil", "Responsabilidad civil"),
            ("fianzas", "Fianzas"),
        ],
        required=True,
        string="Ramo",
    )
    policy_number = fields.Char(required=True, string="Numero de poliza")
    client_id = fields.Many2one(
        "insurance.client",
        ondelete="restrict",
        required=True,
        string="Cliente",
    )
    term_ids = fields.One2many(
        "insurance.policy.term",
        "policy_id",
        string="Vigencias",
    )

    def action_new_term(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Nueva vigencia",
            "res_model": "insurance.policy.term",
            "view_mode": "form",
            "views": [(self.env.ref("insurance_policies.view_insurance_policy_term_form").id, "form")],
            "target": "current",
            "context": {
                "default_policy_id": self.id,
                "default_business_type": "new",
            },
        }


class InsurancePolicyTerm(models.Model):
    _name = "insurance.policy.term"
    _description = "Insurance Policy Term"
    _order = "effective_date desc, expiration_date desc, id desc"

    _allowed_state_transitions = {
        "draft": {"active", "cancelled"},
        "active": {"review"},
        "review": {"cancelled"},
        "cancelled": set(),
    }
    _allowed_cancellation_reasons = {
        "draft": {"emission_cancelled"},
        "review": {"renewed", "unpaid", "lost"},
    }

    policy_id = fields.Many2one(
        "insurance.policy",
        ondelete="cascade",
        required=True,
        string="Poliza",
    )
    business_type = fields.Selection(
        [
            ("new", "Nuevo"),
            ("renewal", "Renovacion"),
        ],
        default="new",
        required=True,
        string="Tipo de negocio",
    )
    state = fields.Selection(
        [
            ("draft", "En Emision"),
            ("active", "Activa"),
            ("review", "En Revision"),
            ("cancelled", "Cancelada"),
        ],
        default="draft",
        required=True,
        string="Estado",
    )
    closure_reason = fields.Selection(
        [
            ("emission_cancelled", "Emision cancelada"),
            ("renewed", "Poliza renovada"),
            ("unpaid", "Poliza cancelada sin pago"),
            ("lost", "Poliza perdida"),
        ],
        copy=False,
        string="Motivo de cierre",
    )
    effective_date = fields.Date(required=True, string="Fecha de vigencia")
    expiration_date = fields.Date(required=True, string="Fecha de vencimiento")

    @api.depends("policy_id.policy_number", "effective_date", "expiration_date")
    def _compute_display_name(self):
        for term in self:
            policy_number = term.policy_id.policy_number or "Vigencia"
            if term.effective_date and term.expiration_date:
                term.display_name = f"{policy_number}: {term.effective_date} - {term.expiration_date}"
            else:
                term.display_name = policy_number

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state", "draft") != "cancelled":
                vals["closure_reason"] = False
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "state" in vals:
            self._check_allowed_state_write(vals["state"], vals.get("closure_reason"))
            if vals["state"] != "cancelled":
                vals["closure_reason"] = False
        return super().write(vals)

    def _check_allowed_state_write(self, target_state, closure_reason=False):
        if self.env.context.get("insurance_policy_workflow_transition"):
            return
        for term in self:
            if term.state == target_state:
                continue
            allowed_targets = self._allowed_state_transitions.get(term.state, set())
            if target_state not in allowed_targets:
                raise ValidationError("La transicion de estado no esta permitida.")
            if target_state == "cancelled":
                allowed_reasons = self._allowed_cancellation_reasons.get(term.state, set())
                if closure_reason not in allowed_reasons:
                    raise ValidationError("El motivo de cierre no corresponde a la transicion.")

    def _ensure_state(self, expected_state):
        for term in self:
            if term.state != expected_state:
                raise ValidationError("La vigencia no esta en el estado requerido para esta accion.")

    def _set_workflow_state(self, target_state, closure_reason=False):
        vals = {"state": target_state}
        if target_state == "cancelled":
            vals["closure_reason"] = closure_reason
        else:
            vals["closure_reason"] = False
        return self.with_context(insurance_policy_workflow_transition=True).write(vals)

    def action_confirm_emission(self):
        self._ensure_state("draft")
        return self._set_workflow_state("active")

    def action_cancel_emission(self):
        self._ensure_state("draft")
        return self._set_workflow_state("cancelled", "emission_cancelled")

    def action_send_to_review(self):
        self._ensure_state("active")
        return self._set_workflow_state("review")

    def action_mark_renewed(self):
        self._ensure_state("review")
        return self._set_workflow_state("cancelled", "renewed")

    def action_cancel_unpaid(self):
        self._ensure_state("review")
        return self._set_workflow_state("cancelled", "unpaid")

    def action_mark_lost(self):
        self._ensure_state("review")
        return self._set_workflow_state("cancelled", "lost")

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Vigencia",
            "res_model": "insurance.policy.term",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("insurance_policies.view_insurance_policy_term_form").id, "form")],
            "target": "current",
        }

    @api.constrains("effective_date", "expiration_date")
    def _check_date_order(self):
        for term in self:
            if (
                term.effective_date
                and term.expiration_date
                and term.expiration_date < term.effective_date
            ):
                raise ValidationError("La fecha de vencimiento no puede ser anterior a la fecha de vigencia.")

    @api.constrains("state", "closure_reason")
    def _check_closure_reason(self):
        for term in self:
            if term.state == "cancelled" and not term.closure_reason:
                raise ValidationError("El motivo de cierre es obligatorio para vigencias canceladas.")
            if term.state != "cancelled" and term.closure_reason:
                raise ValidationError("Solo las vigencias canceladas pueden tener motivo de cierre.")
