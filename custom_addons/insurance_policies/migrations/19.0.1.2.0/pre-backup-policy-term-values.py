def migrate(cr, version):
    cr.execute("DROP TABLE IF EXISTS insurance_policy_term_migration_backup")
    cr.execute(
        """
        CREATE TABLE insurance_policy_term_migration_backup AS
        SELECT
            id AS policy_id,
            business_type,
            state,
            closure_reason,
            effective_date,
            expiration_date,
            create_uid,
            create_date,
            write_uid,
            write_date
        FROM insurance_policy
        """
    )
