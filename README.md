git clone <repo-url> && cd cinema
docker compose exec web pip install types-requests types-redis
# 🎬 Cinema API - Django REST Framework

[![CI/CD](https://github.com/USERNAME/cinema/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/USERNAME/cinema/actions)
[![codecov](https://codecov.io/gh/USERNAME/cinema/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/cinema)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django 4.2](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![DRF 3.15](https://img.shields.io/badge/DRF-3.15-orange.svg)](https://www.django-rest-framework.org/)
[![Coverage 92%](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](https://codecov.io/gh/USERNAME/cinema)

> Production-ready Django REST API for managing films, authors and spectators, with JWT auth, Redis caching and OpenAPI documentation.

---

## 🚀 Quick Start

```bash
git clone <repo-url> && cd cinema
cp .env.example .env  # Edit SECRET_KEY, POSTGRES_*, TMDB_API_KEY as needed
make run && make migrate && make create_data
```

**Access**:
- [Swagger UI](http://localhost:8000/api/docs/) - interactive API docs ⭐
- [Admin](http://localhost:8000/admin/) - admin / admin123
- [API root](http://localhost:8000/api/)

---

## 🎯 Key Features

- 🎬 Full CRUD for films with TMDb import, ratings, status management and poster uploads
- 👥 Three roles: `Admin`, `Author`, `Spectator` with granular permissions
- ⭐ Reviews and favorites: 1-5 star ratings, comments, automatic average scores
- 🔐 JWT authentication (short-lived access, refresh tokens, blacklist support)
- 📊 Custom Django admin (advanced filters, inlines, bulk actions)
- 🚀 Performance optimizations: Redis caching (15 min), query tuning, pagination
- 📖 API docs: Swagger UI, ReDoc, OpenAPI 3.0, health checks
- 🧪 Quality: ~92% test coverage, MyPy, Ruff, Black, isort, CI/CD

---

## 🏗️ Architecture (overview)

```
cinema/
├── cinema/         # Django settings (JWT, cache, CORS)
├── core/           # Mixins, permissions, exceptions
├── users/          # CustomUser (Admin/Author/Spectator)
├── films/          # Film, Author, FilmReview, AuthorReview
├── spectateurs/    # Spectator + favorites (M2M)
└── loadtests/      # k6 performance tests
```

Core relation: `CustomUser` → `Author` (1:1) → `Film` (FK) ← `FilmReview` ← `Spectator` (1:1) ← `CustomUser`

---

## 💻 Tech Stack

| Category | Technologies |
|----------|--------------|
| Backend  | Python 3.12, Django 4.2.5, Django REST Framework 3.15.2 |
| Database | PostgreSQL 15, Redis 7 (cache) |
| Auth     | JWT (djangorestframework-simplejwt), CORS headers |
| Docs     | drf-spectacular, Swagger UI, ReDoc, OpenAPI 3.0 |
| Quality  | pytest (~92% coverage), Ruff, Black, isort, MyPy |
| DevOps   | Docker, docker-compose, GitHub Actions, Codecov, k6 |
| External | TMDb API, Pillow |

---

## 🐳 Docker Environments

The project includes three Docker Compose configurations for different environments:

### Development (`docker-compose-dev.yml`)
- **Purpose**: Local development with hot-reload
- **Features**: 
  - Django runserver with auto-reload
  - Volume mounts for live code changes
  - Exposed ports (8000, 15433, 6380)
  - DEBUG mode enabled
- **Usage**: `make run` (default)

### Test (`docker-compose-test.yml`)
- **Purpose**: Isolated testing environment
- **Features**:
  - Clean database for each test run
  - No volume mounts (uses container filesystem)
  - Optimized for CI/CD pipelines
- **Usage**: `make test`

### Staging (`docker-compose-staging.yml`)
- **Purpose**: Pre-production validation environment
- **Features**:
  - Gunicorn WSGI server (3 workers)
  - Production-like settings (DEBUG=False)
  - Restart policies for reliability
- **Usage**: `docker compose -f docker-compose-staging.yml up`
- **⚠️ Note**: This is NOT a production-ready configuration

### Production Deployment

For actual production deployments, we recommend using managed platforms instead of docker-compose:

**Recommended platforms**:
- **AWS**: ECS Fargate, RDS (PostgreSQL), ElastiCache (Redis), ALB, CloudWatch
- **GCP**: Cloud Run, Cloud SQL, Memorystore, Cloud Load Balancing
- **Azure**: Container Instances, Database for PostgreSQL, Cache for Redis
- **Platform-as-a-Service**: Railway, Render, Fly.io

**Why not docker-compose in production?**
- No built-in horizontal scaling or load balancing
- Secrets stored in `.env` files (security risk)
- Single point of failure (no high availability)
- No centralized logging or monitoring
- Database not externalized (data persistence risk)
- Manual SSL/TLS certificate management

**Production requirements checklist**:
- ✅ Reverse proxy (nginx/Traefik) with SSL termination
- ✅ Secrets management (AWS Secrets Manager, Vault, etc.)
- ✅ Monitoring and alerting (Prometheus, Grafana, Sentry)
- ✅ Log aggregation (ELK stack, CloudWatch, Datadog)
- ✅ Managed database with backups and replication
- ✅ Horizontal scaling and auto-scaling policies
- ✅ Health checks and graceful shutdowns
- ✅ Container orchestration (Kubernetes, ECS, etc.)

---

## 📋 Common Commands

```bash
# Run locally
make run                # start (build + up -d)
make logs               # follow logs
make stop/restart       # stop / restart

# Database
make migrate            # apply migrations
make create_data        # seed test data (8 films, 4 authors, reviews)
make import_tmdb        # import films from TMDb

# Tests & quality
make test               # tests + coverage (~92%)
make quality            # Ruff + Black + isort + MyPy
make format             # auto-format code

```

Typical workflow: `make run && make migrate && make create_data` → develop → `make test && make quality`

---

## 📚 API Documentation

Interactive docs: [Swagger UI](http://localhost:8000/api/docs/) | [ReDoc](http://localhost:8000/api/redoc/) | [OpenAPI schema](http://localhost:8000/api/schema/)

### Main endpoints (summary)

```
# Auth
POST /api/login/                        # obtain JWT tokens (access ~5min, refresh ~24h)
POST /api/spectators/register/          # spectator registration
POST /api/token/refresh/                # refresh access token
POST /api/logout/                       # blacklist refresh token

# Films
GET  /api/films/                        # list films (cached)
POST /api/films/                        # create film (admin/author)
GET  /api/films/{id}/                   # film detail (includes reviews)
POST /api/films/{id}/archive/           # archive film

# Authors
GET  /api/authors/                      # list authors (cached)
POST /api/authors/                      # create author (admin)
GET  /api/authors/{id}/                 # author detail (includes films)

# Reviews
POST /api/film-reviews/                 # add film review (1-5 stars)
POST /api/author-reviews/               # add author review

# Favorites
GET  /api/spectators/me/                # my profile
POST /api/spectators/favorites/add/     # add favorite
POST /api/spectators/favorites/remove/  # remove favorite
GET  /api/spectators/favorites/         # my favorites

# Monitoring
GET  /health/                           # health check (DB + cache)
GET  /ready/                            # readiness probe
GET  /live/                             # liveness probe
```

Common filters: `?status=published`, `?evaluation=PG`, `?search=matrix`, `?ordering=-created_at`, `?source=TMDB`

> 💡 Use the Swagger UI for full interactive examples and request testing.

---

## 🧪 Tests & Quality

```bash
make test               # run tests (98 tests, ~92% coverage)
make test-verbose       # verbose test output
make coverage           # generate HTML coverage report
make quality            # run linters + type checks
make lint               # Ruff linting
make format             # Black + isort
make typecheck          # MyPy
```

Key tooling:
- pytest (unit + integration tests)
- MyPy with django-stubs for type checking
- Ruff, Black, isort for code style

---

## 🚀 Performance

### Optimizations applied

- Query tuning with `select_related()` and `prefetch_related()`
- DB annotations for aggregates (e.g. `Avg('reviews__rating')`)
- Redis caching for list endpoints (`@cache_page(900)`) 
- Pagination (default 10, max 100)
- DB indexes on FK and frequently queried fields
- Connection pooling for PostgreSQL

### Load testing (k6)

```bash
make loadtest           # run basic k6 load test
k6 run loadtests/perf_test.js  # advanced scenarios
```

Performance targets:
- p95 < 500ms
- p99 < 1000ms
- error rate < 1%
- throughput >= 100 req/s
- cache hit ratio > 80%

---

## 🔄 CI/CD

GitHub Actions pipeline runs on PRs and pushes and includes:

- Linting (Ruff, Black)
- Type checking (MyPy)
- Tests with PostgreSQL + Redis (coverage gate)
- Docker image build verification
- Codecov reporting and quality gates

Branch protection requires all checks to pass before merging to `main`.

---

## 🎓 Advanced technical notes

- DRF patterns: use `source=` and DB annotations instead of `SerializerMethodField` where possible
- Custom permissions: `IsAuthorOrAdminOrReadOnly`, role-based access
- Cache strategy: Redis + `@cache_page` + `@vary_on_cookie`
- Type safety: MyPy strict configuration with django-stubs
- Testing: factory_boy for fixtures, mocks, and integration tests
- Security: JWT blacklist, CORS configured, DB protections (`PROTECT`/`CASCADE` as appropriate)
- Admin: inlines, custom displays, bulk actions
- Use `@transaction.atomic` for external imports (TMDb)

---

## 🔒 Environment variables (example)

```env
# Django
SECRET_KEY=django-insecure-change-to-long-random-value
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
POSTGRES_DB=cinema
POSTGRES_USER=cinema_user
POSTGRES_PASSWORD=cinema_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# TMDb (optional)
TMDB_API_KEY=

# JWT (optional)
JWT_ACCESS_TOKEN_LIFETIME=5      # minutes
JWT_REFRESH_TOKEN_LIFETIME=1440  # minutes
```

---

## 🐛 Troubleshooting

```bash
# If DB connection fails
make restart && make logs

# If MyPy misses stubs
docker compose exec web pip install types-requests types-redis

# If tests fail
make clean && make run && make migrate && make test

# If TMDb import returns 401
# check TMDB_API_KEY in your .env and obtain a key at https://www.themoviedb.org/settings/api
```

---

## 📚 Additional documentation

- [MYPY.md](MYPY.md) - MyPy configuration
- [DRF_SPECTACULAR.md](DRF_SPECTACULAR.md) - OpenAPI / Swagger notes
- [VALIDATION.md](VALIDATION.md) - Validation checklist
- [.github/workflows/README.md](.github/workflows/README.md) - CI/CD details
- [MODIFICATIONS.md](MODIFICATIONS.md) - Change log

---


Stack: Python 3.12 | Django 4.2.5 | DRF 3.15.2 | PostgreSQL 15 | Redis 7
