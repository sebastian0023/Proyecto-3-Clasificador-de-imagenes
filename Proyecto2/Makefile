.PHONY: up down logs test lint fmt shell

up:          ## Levanta todo el entorno local (app + MariaDB + MinIO)
	python scripts/up.py

down:        ## Apaga los contenedores (conserva los datos)
	python scripts/down.py

logs:        ## Sigue los logs de la app
	docker compose logs -f app

test:        ## Corre la suite de pytest
	pytest

lint:        ## Ruff en modo verificacion
	ruff check . && ruff format --check .

fmt:         ## Ruff en modo escritura
	ruff check --fix . && ruff format .

shell:       ## Shell dentro del contenedor de la app
	docker compose exec app bash
