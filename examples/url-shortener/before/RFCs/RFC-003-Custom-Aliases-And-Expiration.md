# RFC-003: Custom Aliases and Expiration

## Summary
Allow users to specify custom aliases for their short URLs and set expiration dates. Includes automatic cleanup of expired URLs.

**Complexity**: Low
**Features**: F9 (Custom aliases), F10 (Expiration dates), F13 (URL validation)
**Builds upon**: RFC-001
**Required by**: None

## Technical Approach

### Custom Aliases
- Extend `POST /api/urls` to accept an optional `alias` field
- Alias validation: 3-30 characters, alphanumeric and hyphens only (`^[a-zA-Z0-9-]{3,30}$`)
- Return 409 Conflict if alias is already taken
- Reserved aliases: `api`, `docs`, `health`, `admin` (configurable list)

### Expiration
- Extend `POST /api/urls` to accept an optional `expiresAt` field (ISO 8601 datetime)
- Redirect endpoint checks `expires_at` before redirecting; return 404 if expired
- Scheduled cleanup job runs every hour to hard-delete expired URLs and their click data

### URL Validation
- Validate URL format (must be a valid HTTP/HTTPS URL)
- Optional: check against a malware blocklist API at creation time
- Reject URLs with suspicious patterns (data: URIs, javascript: URIs)

### Cleanup Job
- Cron-style job using node-cron or similar
- Query: `DELETE FROM urls WHERE expires_at < NOW() AND expires_at IS NOT NULL`
- Log number of cleaned up URLs per run

## Acceptance Criteria
- [ ] Users can create short URLs with custom 3-30 char alphanumeric aliases
- [ ] Duplicate aliases return 409 Conflict with a clear error message
- [ ] Reserved aliases are rejected with 400 Bad Request
- [ ] Expired URLs return 404 on redirect
- [ ] Cleanup job runs hourly and removes expired URLs and their click data
- [ ] Invalid URLs (non-HTTP, data: URIs) are rejected at creation time
- [ ] All new functionality covered by unit and integration tests
