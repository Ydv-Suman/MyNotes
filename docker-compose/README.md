# Docker Compose

Create the local environment file and add your OpenAI key:

```bash
cp docker-compose/.env.example docker-compose/.env
```

Run these commands from the project root:

```bash
# Build images
docker compose --env-file docker-compose/.env -f docker-compose/compose.yml build

# Start in the background (also builds when needed)
docker compose --env-file docker-compose/.env -f docker-compose/compose.yml up --build -d

# Check status and logs
docker compose --env-file docker-compose/.env -f docker-compose/compose.yml ps
docker compose --env-file docker-compose/.env -f docker-compose/compose.yml logs -f

# Stop containers without deleting saved PDFs/database
docker compose --env-file docker-compose/.env -f docker-compose/compose.yml down
```

Open `http://localhost:8080`. To remove all persisted data too, run `docker compose --env-file docker-compose/.env -f docker-compose/compose.yml down --volumes`.
# MyNotes
