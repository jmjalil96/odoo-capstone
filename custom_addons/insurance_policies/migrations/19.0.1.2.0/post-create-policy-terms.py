def migrate(cr, version):
    cr.execute(
        """
        INSERT INTO insurance_policy_term (
            policy_id,
            business_type,
            state,
            closure_reason,
            effective_date,
            expiration_date,
            create_uid,
            create_date,
            write_uid,
            write_date
        )
        SELECT
            backup.policy_id,
            backup.business_type,
            backup.state,
            CASE
                WHEN backup.state = 'cancelled' THEN COALESCE(backup.closure_reason, 'emission_cancelled')
                ELSE NULL
            END,
            backup.effective_date,
            backup.expiration_date,
            COALESCE(backup.create_uid, 1),
            COALESCE(backup.create_date, NOW() AT TIME ZONE 'UTC'),
            COALESCE(backup.write_uid, backup.create_uid, 1),
            COALESCE(backup.write_date, backup.create_date, NOW() AT TIME ZONE 'UTC')
        FROM insurance_policy_term_migration_backup backup
        WHERE NOT EXISTS (
            SELECT 1
            FROM insurance_policy_term term
            WHERE term.policy_id = backup.policy_id
        )
        """
    )
    cr.execute("DROP TABLE IF EXISTS insurance_policy_term_migration_backup")
