.PHONY: build run stop test shell cli push deploy

IMAGE=tradeguard
TAG=latest

build:
	docker build -t $(IMAGE):$(TAG) .

run:
	docker compose up -d web

stop:
	docker compose down

logs:
	docker compose logs -f web

test:
	docker compose run --rm cli test

shell:
	docker compose run --rm cli /bin/bash

cli:
	docker compose run --rm cli

clean:
	docker compose down -v
	docker rmi $(IMAGE):$(TAG) || true

deploy-fly:
	fly deploy

deploy-railway:
	railway up
