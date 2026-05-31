def migrate(cr, version):
    columns = [
        "current_term_id",
        "current_business_type",
        "current_state",
        "current_closure_reason",
        "current_effective_date",
        "current_expiration_date",
    ]
    for column in columns:
        cr.execute(f"ALTER TABLE insurance_policy DROP COLUMN IF EXISTS {column}")
