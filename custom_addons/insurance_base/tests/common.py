import ast
import os
from uuid import uuid4

from odoo.modules.module import get_module_path


def read_manifest(module_name):
    manifest_path = os.path.join(get_module_path(module_name), "__manifest__.py")
    with open(manifest_path, encoding="utf-8") as manifest_file:
        return ast.literal_eval(manifest_file.read())


class InsuranceProfileTestMixin:
    """Shared factory helpers for insurance profile tests.

    This is intentionally NOT a TransactionCase subclass so it is never
    collected as a runnable test. Mix it into a concrete test case:

        from odoo.addons.insurance_base.tests.common import InsuranceProfileTestMixin
        from odoo.tests.common import TransactionCase, tagged

        @tagged("post_install", "-at_install")
        class TestSomething(InsuranceProfileTestMixin, TransactionCase):
            ...

    The helpers reference downstream models (insurance.client, insurance.policy,
    etc.), so they only work when those modules are installed, e.g. under the
    post_install test phase.
    """

    def _unique_value(self):
        return uuid4().hex

    def _create_client(self, **overrides):
        vals = {
            "first_name": "Juan",
            "last_name": "Jalil",
            "id_type": "cedula",
            "vat": self._unique_value(),
        }
        vals.update(overrides)
        return self.env["insurance.client"].create(vals)

    def _create_agent(self, **overrides):
        vals = {
            "name": "Agente Demo",
            "vat": self._unique_value(),
        }
        vals.update(overrides)
        return self.env["insurance.agent"].create(vals)

    def _create_policy(self, **overrides):
        vals = {
            "area": "general",
            "ramo": "vehiculos",
            "policy_number": f"POL-{self._unique_value()}",
        }
        if "client_id" not in overrides:
            vals["client_id"] = self._create_client().id
        vals.update(overrides)
        return self.env["insurance.policy"].create(vals)

    def _create_policy_term(self, **overrides):
        vals = {
            "business_type": "new",
            "effective_date": "2026-01-01",
            "expiration_date": "2026-12-31",
        }
        if "policy_id" not in overrides:
            vals["policy_id"] = self._create_policy().id
        vals.update(overrides)
        return self.env["insurance.policy.term"].create(vals)
