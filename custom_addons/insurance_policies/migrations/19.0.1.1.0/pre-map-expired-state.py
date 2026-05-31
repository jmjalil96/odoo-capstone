def migrate(cr, version):
    cr.execute("UPDATE insurance_policy SET state = 'review' WHERE state = 'expired'")
