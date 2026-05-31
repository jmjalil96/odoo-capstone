COMPOSE ?= docker compose
DB ?= insurance_dev
MODULES ?= insurance_base,insurance_clients,insurance_policies,insurance_agents
TEST_PORT ?= 8079

.PHONY: up down logs ps shell install install-demo upgrade test config

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f odoo

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec odoo bash

install:
	$(COMPOSE) exec -T odoo odoo -d $(DB) -i $(MODULES) --stop-after-init --http-port=$(TEST_PORT)

install-demo:
	$(COMPOSE) exec -T odoo odoo -d $(DB) -i $(MODULES) --stop-after-init --http-port=$(TEST_PORT)
	$(COMPOSE) exec -T odoo odoo module force-demo -d $(DB)

upgrade:
	$(COMPOSE) exec -T odoo odoo -d $(DB) -u $(MODULES) --stop-after-init --http-port=$(TEST_PORT)

test:
	$(COMPOSE) exec -T odoo odoo -d $(DB) -u $(MODULES) --test-enable --stop-after-init --http-port=$(TEST_PORT)

config:
	$(COMPOSE) config
