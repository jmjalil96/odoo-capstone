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
    cr.execute("CREATE SEQUENCE IF NOT EXISTS insurance_agent_id_seq")
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS insurance_agent (
            id integer NOT NULL DEFAULT nextval('insurance_agent_id_seq'),
            active boolean DEFAULT true,
            partner_id integer,
            name varchar,
            vat varchar,
            phone varchar,
            email varchar,
            street varchar,
            street2 varchar,
            city varchar,
            state_id integer,
            country_id integer,
            is_company boolean,
            birthdate date,
            has_credential boolean,
            credential_number varchar,
            create_uid integer,
            create_date timestamp without time zone,
            write_uid integer,
            write_date timestamp without time zone,
            CONSTRAINT insurance_agent_pkey PRIMARY KEY (id)
        )
        """
    )
    cr.execute("ALTER SEQUENCE insurance_agent_id_seq OWNED BY insurance_agent.id")

    if not _column_exists(cr, "res_partner", "is_insurance_agent"):
        return

    cr.execute(
        """
        SELECT vat
          FROM res_partner
         WHERE COALESCE(is_insurance_agent, false)
           AND COALESCE(active, true)
           AND vat IS NOT NULL
           AND vat != ''
         GROUP BY vat
        HAVING COUNT(*) > 1
         LIMIT 1
        """
    )
    duplicate = cr.fetchone()
    if duplicate:
        raise Exception(
            "Cannot migrate insurance agents: duplicate active agent RUC %s" % duplicate[0]
        )

    cr.execute(
        """
        INSERT INTO insurance_agent (
            id,
            active,
            partner_id,
            name,
            vat,
            phone,
            email,
            street,
            street2,
            city,
            state_id,
            country_id,
            is_company,
            birthdate,
            has_credential,
            credential_number,
            create_uid,
            create_date,
            write_uid,
            write_date
        )
        SELECT
            partner.id,
            COALESCE(partner.active, true),
            partner.id,
            partner.name,
            partner.vat,
            partner.phone,
            partner.email,
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id,
            partner.country_id,
            COALESCE(partner.is_company, false),
            partner.agent_birthdate,
            COALESCE(partner.agent_has_credential, false),
            CASE
                WHEN COALESCE(partner.agent_has_credential, false) THEN partner.agent_credential_number
                ELSE NULL
            END,
            COALESCE(partner.create_uid, 1),
            COALESCE(partner.create_date, NOW() AT TIME ZONE 'UTC'),
            COALESCE(partner.write_uid, partner.create_uid, 1),
            COALESCE(partner.write_date, partner.create_date, NOW() AT TIME ZONE 'UTC')
          FROM res_partner partner
         WHERE COALESCE(partner.is_insurance_agent, false)
           AND NOT EXISTS (
                SELECT 1
                  FROM insurance_agent agent
                 WHERE agent.partner_id = partner.id
           )
        """
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
