from uuid import uuid4
from xml.etree import ElementTree

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.insurance_base.tests.common import read_manifest


@tagged("post_install", "-at_install")
class TestInsurancePolicies(TransactionCase):
    def _unique_value(self):
        return uuid4().hex

    def _create_client(self):
        return self.env["insurance.client"].create(
            {
                "first_name": "Ana",
                "last_name": "Perez",
                "id_type": "cedula",
                "vat": self._unique_value(),
            }
        )

    def _policy_vals(self, client):
        return {
            "area": "general",
            "ramo": "vehiculos",
            "policy_number": f"POL-{self._unique_value()}",
            "client_id": client.id,
        }

    def _term_vals(self, policy, **overrides):
        vals = {
            "policy_id": policy.id,
            "business_type": "new",
            "effective_date": "2026-01-01",
            "expiration_date": "2026-12-31",
        }
        vals.update(overrides)
        return vals

    def _create_policy(self):
        return self.env["insurance.policy"].create(self._policy_vals(self._create_client()))

    def _create_term(self, policy=None, **overrides):
        policy = policy or self._create_policy()
        return self.env["insurance.policy.term"].create(self._term_vals(policy, **overrides))

    def test_create_policy_for_insurance_client_without_terms(self):
        client = self._create_client()

        policy = self.env["insurance.policy"].create(self._policy_vals(client))

        self.assertEqual(policy.client_id, client)
        self.assertEqual(policy.display_name, policy.policy_number)
        self.assertFalse(policy.term_ids)
        self.assertNotIn("current_state", self.env["insurance.policy"]._fields)
        self.assertNotIn("current_term_id", self.env["insurance.policy"]._fields)

    def test_insurance_policies_is_not_the_visible_app_tile(self):
        self.assertFalse(read_manifest("insurance_policies")["application"])

    def test_insurance_policies_menu_parents_to_base_root(self):
        root = self.env.ref("insurance_base.menu_insurance_root")
        menu = self.env.ref("insurance_policies.menu_insurance_policies")

        self.assertEqual(menu.parent_id, root)

    def test_create_policy_term_linked_to_policy(self):
        policy = self._create_policy()

        term = self._create_term(policy)

        self.assertEqual(term.policy_id, policy)
        self.assertEqual(policy.term_ids, term)
        self.assertEqual(term.state, "draft")
        self.assertEqual(term.business_type, "new")
        self.assertEqual(str(term.effective_date), "2026-01-01")
        self.assertEqual(str(term.expiration_date), "2026-12-31")
        self.assertFalse(term.closure_reason)

    def test_policy_client_relation_targets_client_profile(self):
        field = self.env["insurance.policy"]._fields["client_id"]

        self.assertEqual(field.comodel_name, "insurance.client")

    def test_policy_does_not_own_workflow_actions(self):
        policy = self._create_policy()

        self.assertFalse(hasattr(type(policy), "action_confirm_emission"))
        self.assertFalse(hasattr(type(policy), "action_send_to_review"))
        self.assertFalse(hasattr(type(policy), "action_mark_renewed"))

    def test_policy_new_term_action_defaults_policy(self):
        policy = self._create_policy()

        action = policy.action_new_term()

        self.assertEqual(action["res_model"], "insurance.policy.term")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["context"]["default_policy_id"], policy.id)

    def test_term_open_action_targets_term_detail(self):
        term = self._create_term()

        action = term.action_open_form()

        self.assertEqual(action["res_model"], "insurance.policy.term")
        self.assertEqual(action["res_id"], term.id)
        self.assertEqual(action["view_mode"], "form")

    def test_policy_terms_list_does_not_open_quick_dialog(self):
        view = self.env.ref("insurance_policies.view_insurance_policy_form")
        arch = ElementTree.fromstring(view.arch_db)
        term_field = arch.find(".//field[@name='term_ids']")
        term_list = term_field.find("list")

        self.assertEqual(term_list.attrib["no_open"], "1")
        self.assertEqual(term_list.attrib["create"], "0")
        self.assertEqual(term_list.attrib["edit"], "0")
        self.assertEqual(term_list.attrib["delete"], "0")

    def test_policy_and_term_views_disable_duplicate(self):
        view_xml_ids = [
            "insurance_policies.view_insurance_policy_list",
            "insurance_policies.view_insurance_policy_form",
            "insurance_policies.view_insurance_policy_term_list",
            "insurance_policies.view_insurance_policy_term_form",
        ]
        for view_xml_id in view_xml_ids:
            with self.subTest(view_xml_id=view_xml_id):
                view = self.env.ref(view_xml_id)
                arch = ElementTree.fromstring(view.arch_db)
                self.assertEqual(arch.attrib["duplicate"], "0")

    def test_confirm_emission_transition(self):
        term = self._create_term()

        term.action_confirm_emission()

        self.assertEqual(term.state, "active")
        self.assertFalse(term.closure_reason)

    def test_cancel_emission_transition_sets_reason(self):
        term = self._create_term()

        term.action_cancel_emission()

        self.assertEqual(term.state, "cancelled")
        self.assertEqual(term.closure_reason, "emission_cancelled")

    def test_send_to_review_transition(self):
        term = self._create_term()
        term.action_confirm_emission()

        term.action_send_to_review()

        self.assertEqual(term.state, "review")
        self.assertFalse(term.closure_reason)

    def test_review_cancellation_transitions_set_reason(self):
        actions = [
            ("action_mark_renewed", "renewed"),
            ("action_cancel_unpaid", "unpaid"),
            ("action_mark_lost", "lost"),
        ]
        for action_name, closure_reason in actions:
            term = self._create_term()
            term.action_confirm_emission()
            term.action_send_to_review()

            getattr(term, action_name)()

            self.assertEqual(term.state, "cancelled")
            self.assertEqual(term.closure_reason, closure_reason)

    def test_invalid_transition_is_blocked(self):
        term = self._create_term()

        with self.assertRaises(ValidationError):
            term.action_send_to_review()

        with self.assertRaises(ValidationError):
            term.write({"state": "review"})

        with self.assertRaises(ValidationError):
            term.write({"state": "cancelled", "closure_reason": "lost"})

    def test_cancelled_without_closure_reason_is_blocked(self):
        term = self._create_term()

        with self.assertRaises(ValidationError):
            term.write({"state": "cancelled"})

    def test_non_cancelled_term_cannot_keep_closure_reason(self):
        term = self._create_term()

        with self.assertRaises(ValidationError):
            term.write({"closure_reason": "lost"})

    def test_reject_expiration_before_effective_date(self):
        policy = self._create_policy()

        with self.assertRaises(ValidationError):
            self.env["insurance.policy.term"].create(
                self._term_vals(policy, expiration_date="2025-12-31")
            )

    def test_allow_policy_without_terms_after_deleting_terms(self):
        policy = self._create_policy()
        term = self._create_term(policy)

        term.unlink()

        self.assertFalse(policy.term_ids)
