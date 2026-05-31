def migrate(cr, version):
    cr.execute(
        """
        SELECT setval(
            'insurance_client_id_seq',
            GREATEST(COALESCE((SELECT MAX(id) FROM insurance_client), 1), 1),
            true
        )
        """
    )
    columns = [
        "is_insurance_client",
        "insurance_first_name",
        "insurance_last_name",
        "insurance_id_type",
        "insurance_gender",
        "insurance_birthdate",
        "insurance_occupation",
        "insurance_activity",
    ]
    for column in columns:
        cr.execute(f"ALTER TABLE res_partner DROP COLUMN IF EXISTS {column}")
