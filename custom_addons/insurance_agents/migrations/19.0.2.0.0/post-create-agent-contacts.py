def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if _column_exists(cr, "res_partner", "agent_birthdate"):
        cr.execute(
            """
            INSERT INTO insurance_agent_contact (
                agent_id,
                partner_id,
                name,
                function,
                email,
                phone,
                birthdate,
                create_uid,
                create_date,
                write_uid,
                write_date
            )
            SELECT
                agent.id,
                contact.id,
                contact.name,
                contact.function,
                contact.email,
                contact.phone,
                contact.agent_birthdate,
                COALESCE(contact.create_uid, 1),
                COALESCE(contact.create_date, NOW() AT TIME ZONE 'UTC'),
                COALESCE(contact.write_uid, contact.create_uid, 1),
                COALESCE(contact.write_date, contact.create_date, NOW() AT TIME ZONE 'UTC')
              FROM insurance_agent agent
              JOIN res_partner contact ON contact.parent_id = agent.partner_id
             WHERE contact.type = 'contact'
               AND NOT EXISTS (
                    SELECT 1
                      FROM insurance_agent_contact agent_contact
                     WHERE agent_contact.agent_id = agent.id
                       AND agent_contact.partner_id = contact.id
               )
            """
        )

    cr.execute(
        """
        UPDATE insurance_policy_term term
           SET agent_id = agent.id
          FROM insurance_agent agent
         WHERE term.agent_id = agent.partner_id
           AND term.agent_id != agent.id
        """
    )
    cr.execute(
        """
        SELECT COUNT(*)
          FROM insurance_policy_term term
          LEFT JOIN insurance_agent agent ON agent.id = term.agent_id
         WHERE term.agent_id IS NOT NULL
           AND agent.id IS NULL
        """
    )
    unmapped_count = cr.fetchone()[0]
    if unmapped_count:
        raise Exception(
            "Cannot migrate insurance terms: %s vigencias have no agent profile" % unmapped_count
        )

    cr.execute(
        """
        SELECT setval(
            'insurance_agent_id_seq',
            GREATEST(COALESCE((SELECT MAX(id) FROM insurance_agent), 1), 1),
            true
        )
        """
    )
    cr.execute(
        """
        SELECT setval(
            'insurance_agent_contact_id_seq',
            GREATEST(COALESCE((SELECT MAX(id) FROM insurance_agent_contact), 1), 1),
            true
        )
        """
    )

    columns = [
        "is_insurance_agent",
        "agent_birthdate",
        "agent_has_credential",
        "agent_credential_number",
    ]
    for column in columns:
        cr.execute(f"ALTER TABLE res_partner DROP COLUMN IF EXISTS {column}")
