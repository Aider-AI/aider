docker.build:
	docker compose -f docker-compose.yaml build aider-dev


docker.up:
	COMPOSE_PROJECT_NAME=aider docker compose -f docker-compose.yaml up


docker.sh:
	COMPOSE_PROJECT_NAME=aider docker compose -f docker-compose.yaml exec aider-dev bash

