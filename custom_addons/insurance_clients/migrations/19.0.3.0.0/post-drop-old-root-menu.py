def _menu_id(cr, module, name):
    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = %s
           AND name = %s
           AND model = 'ir.ui.menu'
        """,
        (module, name),
    )
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    """Remove the legacy insurance_clients.menu_insurance_root root menu.

    Ownership of the root "Seguros" menu moved to insurance_base. Odoo's orphan
    cleanup already removes records whose external id disappears from a module's
    data, so this migration is defensive: it re-parents any straggler child
    menus to the new root and then drops the old menu and its external id.
    """
    old_menu_id = _menu_id(cr, "insurance_clients", "menu_insurance_root")
    if not old_menu_id:
        return

    new_menu_id = _menu_id(cr, "insurance_base", "menu_insurance_root")
    if new_menu_id:
        cr.execute(
            "UPDATE ir_ui_menu SET parent_id = %s WHERE parent_id = %s",
            (new_menu_id, old_menu_id),
        )

    cr.execute("DELETE FROM ir_ui_menu WHERE id = %s", (old_menu_id,))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'insurance_clients'
           AND name = 'menu_insurance_root'
           AND model = 'ir.ui.menu'
        """
    )
