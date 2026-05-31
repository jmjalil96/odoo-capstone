from odoo.tests.common import TransactionCase, tagged

from odoo.addons.insurance_base.tests.common import read_manifest


@tagged("post_install", "-at_install")
class TestInsuranceBase(TransactionCase):
    def test_only_insurance_base_is_the_application(self):
        self.assertTrue(read_manifest("insurance_base")["application"])

    def test_root_menu_lives_in_insurance_base(self):
        root = self.env.ref("insurance_base.menu_insurance_root")

        self.assertEqual(root.name, "Seguros")
        self.assertFalse(root.parent_id)

    def test_no_legacy_root_menu_remains(self):
        self.assertFalse(self.env.ref("insurance_clients.menu_insurance_root", raise_if_not_found=False))
