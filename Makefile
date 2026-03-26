.PHONY: build up down restart logs eval index clean

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose down && docker-compose up -d

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

eval:
	docker-compose exec backend python -m scripts.evaluate

index:
	docker-compose exec backend python -m scripts.build_index --force

clean:
	docker-compose down -v
	rm -f backend/data/financial.db
