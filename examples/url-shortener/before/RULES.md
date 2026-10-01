# Development Rules: LinkSnip URL Shortener

## Technology Stack
- **Runtime**: Node.js 20+ with TypeScript 5.x (strict mode)
- **Framework**: Express.js for REST API
- **Database**: PostgreSQL 16 for URL and analytics storage
- **Cache**: Redis 7 for redirect caching
- **Frontend**: React 18 with Vite for the analytics dashboard
- **Testing**: Jest for unit/integration tests, Playwright for e2e
- **Deployment**: Docker with docker-compose

## Technical Standards

### Naming Conventions
- Files: kebab-case (`url-service.ts`, `click-tracker.ts`)
- Functions/variables: camelCase
- Classes/interfaces/types: PascalCase
- Database tables: snake_case
- API endpoints: kebab-case (`/api/urls`, `/api/urls/:code/analytics`)

### Architecture
- Layered architecture: routes -> controllers -> services -> repositories
- Each layer in its own directory under `src/`
- Shared types in `src/types/`
- Configuration via environment variables (no hardcoded values)

### API Standards
- RESTful conventions with proper HTTP status codes
- All responses wrapped in `{ data, error, meta }` envelope
- Pagination via `?page=1&limit=20` query parameters
- Rate limiting via middleware (100 req/min/IP)

### Database
- All queries via parameterized statements (no string interpolation)
- Migrations managed with a migration tool (e.g., node-pg-migrate)
- Indexes on frequently queried columns (short_code, created_at)

## Quality Standards
- Minimum 80% test coverage for business logic
- All API endpoints must have integration tests
- No `any` types in TypeScript (use `unknown` and narrow)
- No `console.log` in production code; use a structured logger (e.g., pino)
- All errors must be caught and return appropriate HTTP status codes

## Performance
- Redirect endpoint must use Redis cache (cache-aside pattern)
- Analytics writes should be async/batched to avoid slowing redirects
- Database connection pooling (min: 5, max: 20 connections)

## Security
- Validate and sanitize all user input (URLs, aliases)
- Rate limit all API endpoints
- Set security headers (CORS, helmet)
- No sensitive data in logs or error responses
