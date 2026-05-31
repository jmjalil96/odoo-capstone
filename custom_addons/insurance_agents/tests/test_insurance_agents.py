from uuid import uuid4
from xml.etree import ElementTree

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.insurance_base.tests.common import InsuranceProfileTestMixin, read_manifest


@tagged("post_install", "-at_install")
class TestInsuranceAgents(TransactionCase):
    def _unique_value(self):
        return uuid4().hex

    def _create_agent(self, **overrides):
        vals = {
            "name": "Agente Demo",
            "vat": self._unique_value(),
        }
        vals.update(overrides)
        return self.env["insurance.agent"].create(vals)

    def _create_client(self):
        return self.env["insurance.client"].create(
            {
                "first_name": "Ana",
                "last_name": "Perez",
                "id_type": "cedula",
                "vat": self._unique_value(),
            }
        )

    def _create_policy(self):
        return self.env["insurance.policy"].create(
            {
                "area": "general",
                "ramo": "vehiculos",
                "policy_number": f"POL-{self._unique_value()}",
                "client_id": self._create_client().id,
            }
        )

    def _term_vals(self, **overrides):
        vals = {
            "policy_id": self._create_policy().id,
            "business_type": "new",
            "effective_date": "2026-01-01",
            "expiration_date": "2026-12-31",
        }
        vals.update(overrides)
        return vals

    def test_regular_contact_is_unaffected(self):
        partner = self.env["res.partner"].create({"name": "Contacto normal"})

        self.assertNotIn("is_insurance_agent", partner._fields)
        self.assertFalse(self.env["insurance.agent"].search([("partner_id", "=", partner.id)]))

    def test_create_individual_and_company_agents(self):
        individual = self._create_agent(name="Carlos Agente")
        company = self._create_agent(company_type="company", name="Agencia Central S.A.")

        self.assertFalse(individual.is_company)
        self.assertTrue(company.is_company)
        self.assertTrue(company.partner_id.is_company)

    def test_ruc_required_for_agents(self):
        with self.assertRaises(ValidationError):
            self.env["insurance.agent"].create({"name": "Agente sin RUC"})

    def test_duplicate_ruc_blocked_among_agents(self):
        ruc = self._unique_value()
        self._create_agent(vat=ruc)

        with self.assertRaises(ValidationError):
            self._create_agent(name="Agente duplicado", vat=ruc)

    def test_regular_contact_can_share_agent_ruc(self):
        ruc = self._unique_value()
        self._create_agent(vat=ruc)

        partner = self.env["res.partner"].create({"name": "Contacto normal", "vat": ruc})

        self.assertFalse(self.env["insurance.agent"].search([("partner_id", "=", partner.id)]))

    def test_credential_number_required_only_when_credential_is_true(self):
        with self.assertRaises(ValidationError):
            self._create_agent(has_credential=True)

        agent = self._create_agent(
            has_credential=True,
            credential_number="CRED-001",
        )
        self.assertEqual(agent.credential_number, "CRED-001")

        agent.write({"has_credential": False})

        self.assertFalse(agent.credential_number)

    def test_agent_contact_uses_profile_model_and_keeps_birthdate_off_partner(self):
        agent = self._create_agent(company_type="company", name="Agencia Matriz")

        contact = self.env["insurance.agent.contact"].create(
            {
                "agent_id": agent.id,
                "name": "Contacto de Agencia",
                "birthdate": "1990-02-03",
                "email": "contacto@example.com",
            }
        )

        self.assertEqual(contact.birthdate.strftime("%Y-%m-%d"), "1990-02-03")
        self.assertEqual(contact.partner_id.parent_id, agent.partner_id)
        self.assertIn(contact, agent.contact_ids)
        self.assertNotIn("agent_birthdate", contact.partner_id._fields)

    def test_action_opens_insurance_agent_profiles(self):
        action = self.env.ref("insurance_agents.action_insurance_agents")
        context = safe_eval(action.context)

        self.assertEqual(action.res_model, "insurance.agent")
        self.assertEqual(safe_eval(action.domain or "[]"), [])
        self.assertEqual(context["default_company_type"], "person")

    def test_insurance_agents_is_not_the_visible_app_tile(self):
        self.assertFalse(read_manifest("insurance_agents")["application"])

    def test_insurance_agents_menu_parents_to_base_root(self):
        root = self.env.ref("insurance_base.menu_insurance_root")
        menu = self.env.ref("insurance_agents.menu_insurance_agents")

        self.assertEqual(menu.parent_id, root)

    def test_agent_views_disable_duplicate(self):
        view_xml_ids = [
            "insurance_agents.view_insurance_agent_list",
            "insurance_agents.view_insurance_agent_form",
        ]
        for view_xml_id in view_xml_ids:
            with self.subTest(view_xml_id=view_xml_id):
                view = self.env.ref(view_xml_id)
                arch = ElementTree.fromstring(view.arch_db)
                self.assertEqual(arch.attrib["duplicate"], "0")

    def test_agent_child_contact_views_show_birthdate(self):
        view = self.env.ref("insurance_agents.view_insurance_agent_form")
        arch = ElementTree.fromstring(view.arch_db)
        child_field = arch.find(".//page[@name='contacts']/field[@name='contact_ids']")
        child_list = child_field.find("list")
        child_form = child_field.find("form")
        birthdate_list_field = child_list.find("./field[@name='birthdate']")

        self.assertIsNotNone(birthdate_list_field)
        self.assertEqual(birthdate_list_field.attrib["string"], "Nacimiento")
        self.assertEqual(birthdate_list_field.attrib["width"], "120px")
        self.assertIsNotNone(child_form.find(".//field[@name='birthdate']"))

    def test_vigencia_can_link_to_insurance_agent_profile(self):
        agent = self._create_agent()

        term = self.env["insurance.policy.term"].create(self._term_vals(agent_id=agent.id))

        self.assertEqual(term.agent_id, agent)
        self.assertEqual(term._fields["agent_id"].comodel_name, "insurance.agent")

    def test_old_partner_agent_fields_are_removed(self):
        partner_fields = self.env["res.partner"]._fields

        for field_name in [
            "is_insurance_agent",
            "agent_birthdate",
            "agent_has_credential",
            "agent_credential_number",
        ]:
            with self.subTest(field_name=field_name):
                self.assertNotIn(field_name, partner_fields)


@tagged("post_install", "-at_install")
class TestInsuranceProfileHelpers(InsuranceProfileTestMixin, TransactionCase):
    def test_shared_helpers_create_profiles_and_policies(self):
        client = self._create_client()
        agent = self._create_agent()
        policy = self._create_policy()
        term = self._create_policy_term()

        self.assertTrue(client.partner_id)
        self.assertTrue(agent.partner_id)
        self.assertEqual(policy._name, "insurance.policy")
        self.assertTrue(policy.client_id)
        self.assertEqual(term.policy_id._name, "insurance.policy")
