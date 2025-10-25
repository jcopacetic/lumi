export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473.

set shell := ["powershell.exe", "-NoProfile", "-Command"]

# Default command to list all available commands.
default:
    @just --list

# build: Build python image.
build:
    @echo "🔨 Building python image..."
    @docker compose build

# up: Start up containers.
up:
    @echo "🚀 Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop containers.
down:
    @echo "🛑 Stopping containers..."
    @docker compose down

# restart: Restart containers.
restart:
    @echo "🔁 Restarting containers..."
    @docker compose down
    @docker compose up -d --remove-orphans

# ps: Show container status.
ps:
    @docker compose ps

# prune: Remove containers and their volumes.
prune *args:
    @echo "💣 Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs.
logs *args:
    @echo "📜 Tailing logs..."
    @docker compose logs -f {{args}}

# manage: Executes a Django manage.py command.
manage +args:
    @echo "⚙️ Running Django manage.py {{args}}..."
    @docker compose run --rm django python manage.py {{args}}

# shell: Open Django shell inside the container.
shell:
    @echo "🐚 Opening Django shell..."
    @docker compose run --rm django python manage.py shell

# makemigrations: Create new database migrations.
makemigrations:
    @echo "🧩 Making migrations..."
    @docker compose run --rm django python manage.py makemigrations

# migrate: Apply database migrations.
migrate:
    @echo "🗂️  Applying migrations..."
    @docker compose run --rm django python manage.py migrate

# superuser: Create a Django superuser.
superuser:
    @echo "👤 Creating superuser..."
    @docker compose run --rm django python manage.py createsuperuser

# collectstatic: Collect static files.
collectstatic:
    @echo "📦 Collecting static files..."
    @docker compose run --rm django python manage.py collectstatic --noinput

# shell-plus: Open Django shell_plus (if using django-extensions).
shell-plus:
    @echo "🐍 Opening enhanced shell_plus..."
    @docker compose run --rm django python manage.py shell_plus

# test: Run Django tests.
test:
    @echo "🧪 Running tests..."
    @docker compose run --rm django python manage.py test

# showmigrations: Show all migrations and their applied status.
showmigrations:
    @echo "📋 Showing migrations..."
    @docker compose run --rm django python manage.py showmigrations
