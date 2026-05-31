# Odoo Insurance Broker ERP

Local Odoo 19 development setup for the custom insurance broker ERP modules in `custom_addons`.

## Modules

The custom addons build on a shared foundation module and install in this order:

- `insurance_base` - foundation module. Owns the `Seguros` application tile and root menu, and provides the shared `insurance.partner.profile.mixin` (partner-backed profile fields, company-type helpers, and VAT/RUC duplicate checks) plus shared test helpers in `insurance_base.tests.common`.
- `insurance_clients` - insurance client profiles (depends on `insurance_base`).
- `insurance_policies` - insurance policies and vigencias (depends on `insurance_clients`).
- `insurance_agents` - insurance agent profiles and agent contacts (depends on `insurance_policies`).

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2.
- `make`.

## Quickstart

Start Odoo and Postgres:

```sh
make up
```

Install the custom modules into the default development database:

```sh
make install
```

Open Odoo at http://localhost:8069 and use the database `insurance_dev`.

The local database manager password is `admin`. The local Postgres credentials are `odoo` / `odoo`; they are for development only.

## Demo Data

Normal installs stay empty so real development data is not polluted:

```sh
make install
```

For a fresh demo database with sample clients, agents, policies, and vigencias, create or select a throwaway DB name and load demo data explicitly:

```sh
make install-demo DB=insurance_demo
```

Demo data is only for local onboarding, QA, and walkthroughs. It creates profile records (`insurance.client`, `insurance.agent`, and `insurance.agent.contact`), not legacy partner flags.

## Common Commands

```sh
make up        # start Odoo and Postgres
make down      # stop the Compose stack
make logs      # follow Odoo logs
make ps        # show Compose services
make shell     # open a shell in the Odoo container
make install   # install custom modules into insurance_dev
make install-demo DB=insurance_demo  # install custom modules with demo data into a fresh DB
make upgrade   # upgrade custom modules in insurance_dev
make test      # run the custom module tests
make config    # render and validate Compose config
```

The default database and modules can be overridden:

```sh
make test DB=my_db
make upgrade MODULES=insurance_clients
```

## Running Beside Existing Containers

This repository may already have a manual `odoo19` container using port `8069`. To run the Compose stack beside it, create a local `.env` file:

```sh
ODOO_PORT=8070
```

Then run:

```sh
make up
```

Open the Compose Odoo instance at http://localhost:8070.

The `.env` file is intentionally ignored by git.

## Backup Current Manual Database

Before deleting or replacing the existing manual containers, back up the current database:

```sh
mkdir -p backups
docker exec odoo-db pg_dump -U odoo -Fc insurance_dev > backups/insurance_dev.dump
```

Restore that backup into the Compose database after `make up`:

```sh
docker compose exec -T db createdb -U odoo insurance_dev
docker compose exec -T db pg_restore -U odoo -d insurance_dev < backups/insurance_dev.dump
make upgrade
```

If `insurance_dev` already exists in the Compose database, drop it only after confirming you have a backup:

```sh
docker compose exec -T db dropdb -U odoo insurance_dev
```

## Troubleshooting

If port `8069` is already in use, set `ODOO_PORT=8070` in `.env` and run `make up` again.

If Odoo starts but the modules are missing, run:

```sh
make upgrade
```

If tests fail because the web port is busy, the Makefile already runs Odoo test commands on port `8079`. Change it only if another local process is also using `8079`:

```sh
make test TEST_PORT=8089
```
