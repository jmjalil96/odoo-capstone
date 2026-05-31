import os
from uuid import uuid4
from xml.etree import ElementTree

from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_path
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.insurance_base.tests.common import read_manifest


@tagged("post_install", "-at_install")
class TestInsuranceClients(TransactionCase):
    def _unique_id_number(self):
        return uuid4().hex

    def _create_client(self, **overrides):
        vals = {
            "first_name": "Juan",
            "last_name": "Jalil",
            "id_type": "cedula",
            "vat": self._unique_id_number(),
        }
        vals.update(overrides)
        return self.env["insurance.client"].create(vals)

    def _read_demo_xml(self, module_name, filename):
        demo_path = os.path.join(get_module_path(module_name), "demo", filename)
        return ElementTree.parse(demo_path).getroot()

    def test_demo_xml_uses_profile_models_only(self):
        legacy_fields = {
            "is_insurance_client",
            "insurance_first_name",
            "insurance_last_name",
            "insurance_id_type",
            "insurance_gender",
            "insurance_birthdate",
            "insurance_occupation",
            "insurance_activity",
            "is_insurance_agent",
            "agent_birthdate",
            "agent_has_credential",
            "agent_credential_number",
        }
        demo_files = {
            "insurance_clients": (
                "insurance_clients_demo.xml",
                {"insurance.client"},
            ),
            "insurance_policies": (
                "insurance_policies_demo.xml",
                {"insurance.policy", "insurance.policy.term"},
            ),
            "insurance_agents": (
                "insurance_agents_demo.xml",
                {"insurance.agent", "insurance.agent.contact", "insurance.policy.term"},
            ),
        }

        for module_name, (filename, expected_models) in demo_files.items():
            with self.subTest(module_name=module_name):
                root = self._read_demo_xml(module_name, filename)
                records = root.findall(".//record")
                models = {record.attrib["model"] for record in records}
                field_names = {
                    field.attrib["name"]
                    for record in records
                    for field in record.findall("field")
                }

                self.assertEqual(models, expected_models)
                self.assertFalse(legacy_fields.intersection(field_names))

    def test_insurance_clients_is_not_the_visible_app_tile(self):
        self.assertFalse(read_manifest("insurance_clients")["application"])

    def test_insurance_clients_menu_parents_to_base_root(self):
        root = self.env.ref("insurance_base.menu_insurance_root")
        menu = self.env.ref("insurance_clients.menu_insurance_clients")

        self.assertEqual(menu.parent_id, root)

    def test_regular_contact_is_unaffected(self):
        partner = self.env["res.partner"].create({"name": "Contacto normal"})

        self.assertNotIn("is_insurance_client", partner._fields)
        self.assertFalse(self.env["insurance.client"].search([("partner_id", "=", partner.id)]))

    def test_individual_name_sync_and_required_identity(self):
        client = self._create_client(first_name="Juan", last_name="Jalil")

        self.assertEqual(client.name, "Juan Jalil")
        self.assertEqual(client.partner_id.name, "Juan Jalil")

        with self.assertRaises(ValidationError):
            self.env["insurance.client"].create(
                {
                    "first_name": "Maria",
                    "last_name": "Lopez",
                    "id_type": "cedula",
                }
            )

    def test_corporate_client_and_duplicate_vat(self):
        id_number = self._unique_id_number()

        company = self.env["insurance.client"].create(
            {
                "company_type": "company",
                "name": "ACME S.A.",
                "id_type": "ruc_juridica",
                "vat": id_number,
            }
        )

        self.assertTrue(company.is_company)
        self.assertTrue(company.partner_id.is_company)

        with self.assertRaises(ValidationError):
            self._create_client(vat=id_number)

    def test_profile_can_wrap_existing_partner(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Partner Existente",
                "vat": self._unique_id_number(),
            }
        )

        client = self.env["insurance.client"].create(
            {
                "partner_id": partner.id,
                "first_name": "Partner",
                "last_name": "Existente",
                "id_type": "cedula",
            }
        )

        self.assertEqual(client.partner_id, partner)
        self.assertEqual(client.vat, partner.vat)
        self.assertEqual(partner.name, "Partner Existente")

    def test_action_opens_insurance_client_profiles(self):
        action = self.env.ref("insurance_clients.action_insurance_clients")
        context = safe_eval(action.context)

        self.assertEqual(action.res_model, "insurance.client")
        self.assertEqual(safe_eval(action.domain or "[]"), [])
        self.assertEqual(context["default_company_type"], "person")

    def test_insurance_client_views_disable_duplicate(self):
        view_xml_ids = [
            "insurance_clients.view_insurance_client_list",
            "insurance_clients.view_insurance_client_form",
        ]
        for view_xml_id in view_xml_ids:
            with self.subTest(view_xml_id=view_xml_id):
                view = self.env.ref(view_xml_id)
                arch = ElementTree.fromstring(view.arch_db)
                self.assertEqual(arch.attrib["duplicate"], "0")

    def test_child_contact_and_address_are_regular_contacts(self):
        company = self.env["insurance.client"].create(
            {
                "company_type": "company",
                "name": "Cliente Corporativo S.A.",
                "id_type": "ruc_juridica",
                "vat": self._unique_id_number(),
            }
        )

        child = self.env["res.partner"].create(
            {
                "parent_id": company.partner_id.id,
                "type": "contact",
                "name": "Contacto Corporativo",
                "email": "contacto@example.com",
            }
        )
        address = self.env["res.partner"].create(
            {
                "parent_id": company.partner_id.id,
                "type": "invoice",
                "name": "Direccion de facturacion",
                "street": "Av. Principal 123",
            }
        )

        self.assertIn(child, company.child_ids)
        self.assertIn(address, company.child_ids)
        self.assertFalse(self.env["insurance.client"].search([("partner_id", "in", [child.id, address.id])]))

    def test_old_partner_insurance_fields_are_removed(self):
        partner_fields = self.env["res.partner"]._fields

        for field_name in [
            "is_insurance_client",
            "insurance_first_name",
            "insurance_last_name",
            "insurance_id_type",
            "insurance_gender",
            "insurance_birthdate",
            "insurance_occupation",
            "insurance_activity",
        ]:
            with self.subTest(field_name=field_name):
                self.assertNotIn(field_name, partner_fields)
