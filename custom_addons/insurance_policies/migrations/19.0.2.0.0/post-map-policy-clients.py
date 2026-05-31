def migrate(cr, version):
    cr.execute(
        """
        UPDATE insurance_policy policy
           SET client_id = client.id
          FROM insurance_client client
         WHERE policy.client_id = client.partner_id
           AND policy.client_id != client.id
        """
    )
    cr.execute(
        """
        SELECT COUNT(*)
          FROM insurance_policy policy
          LEFT JOIN insurance_client client ON client.id = policy.client_id
         WHERE policy.client_id IS NOT NULL
           AND client.id IS NULL
        """
    )
    unmapped_count = cr.fetchone()[0]
    if unmapped_count:
        raise Exception(
            "Cannot migrate insurance policies: %s policies have no client profile" % unmapped_count
        )
