def migrate(cr, version):
    # Obsolete after 19.0.1.3.0: current vigencia fields now belong in the UI
    # as linked term records, not as stored fields on the master policy.
    return
