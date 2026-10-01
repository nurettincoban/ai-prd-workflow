# RFC-001: Core URL Shortening and Redirection

## Summary
Implement the foundational URL shortening service: creating short URLs from long URLs and redirecting short URLs to their original destinations. This is the foundation that all other RFCs build upon.

**Complexity**: Medium
**Features**: F1 (Create short URL), F2 (Redirect), F4 (Delete), F8 (Docker deployment)
**Builds upon**: None (first RFC)
**Required by**: RFC-002, RFC-003

## Technical Approach

### Database Schema
```sql
CREATE TABLE urls (
  id SERIAL PRIMARY KEY,
  short_code VARCHAR(30) UNIQUE NOT NULL,
  original_url TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NULL,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_urls_short_code ON urls(short_code);
```

### URL Generation
- Generate 7-character codes using base62 encoding (a-z, A-Z, 0-9)
- Use a counter-based approach with base62 encoding for uniqueness
- Collision handling: retry with new random suffix if code exists

### API Endpoints
- `POST /api/urls` - Create short URL (body: `{ url, alias?, expiresAt? }`)
- `GET /:code` - Redirect to original URL (HTTP 301)
- `DELETE /api/urls/:code` - Delete a short URL
- `GET /api/urls` - List all URLs (paginated)

### Architecture
- Express app with layered architecture (routes -> controllers -> services -> repositories)
- Redis cache-aside pattern for redirect lookups
- Docker Compose with Node.js, PostgreSQL, and Redis services

## Acceptance Criteria
- [ ] `POST /api/urls` creates a short URL and returns it in < 200ms
- [ ] `GET /:code` redirects with HTTP 301 in < 100ms (p95)
- [ ] `GET /:code` returns 404 for non-existent codes
- [ ] `DELETE /api/urls/:code` removes the URL and invalidates cache
- [ ] `docker-compose up` starts the full stack successfully
- [ ] Unit and integration tests for all endpoints
