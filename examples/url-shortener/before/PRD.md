# Product Requirements Document: LinkSnip URL Shortener

## Overview
LinkSnip is a web-based URL shortening service that converts long URLs into short, shareable links and provides click analytics. It targets individual developers and small teams who need a simple, self-hostable alternative to commercial URL shorteners.

## Goals and Objectives
- Provide fast, reliable URL shortening with sub-100ms redirect latency
- Deliver basic click analytics (total clicks, referrers, geographic data)
- Support 10,000+ active short URLs per instance
- Offer a clean, minimal UI and a REST API for programmatic access

## Scope

### In Scope (v1.0)
- URL creation (generate short code or accept custom alias)
- URL redirection with click tracking
- Click analytics dashboard
- Expiration dates for short URLs
- REST API for all operations
- Rate limiting and basic abuse prevention

### Out of Scope (v1.0)
- User accounts and authentication (all URLs are public)
- Team workspaces and collaboration features
- Custom domains
- QR code generation
- Bulk URL import

## User Personas

### Developer Dave
- Builds side projects, wants quick URL shortening via API
- Values: simplicity, speed, self-hosting capability
- Pain points: commercial tools are bloated and expensive for personal use

### Marketer Maria
- Shares links on social media, needs to track engagement
- Values: click analytics, custom aliases for branded links
- Pain points: needs basic analytics without complex enterprise tools

## Functional Requirements

### URL Management
- Create short URL from a long URL (auto-generated 7-character base62 code)
- Create short URL with a custom alias (3-30 alphanumeric characters)
- Set optional expiration date on any short URL
- Delete a short URL
- List all created short URLs with metadata

### Redirection
- Redirect short URL to original URL via HTTP 301
- Return 404 for expired or non-existent short URLs
- Track click metadata on each redirect (timestamp, referrer, user-agent, country)

### Analytics
- View total click count per URL
- View click timeline (clicks per day/week/month)
- View top referrers per URL
- View geographic breakdown of clicks (country level)
- Filter analytics by date range

### API
- REST API for all URL management operations
- JSON request/response format
- Rate limiting: 100 requests per minute per IP
- API documentation via OpenAPI/Swagger

## Non-Functional Requirements
- **Performance**: Redirect latency < 100ms at p95
- **Availability**: 99.9% uptime target
- **Scalability**: Handle 1,000 redirects per second per instance
- **Security**: Validate URLs against malware/phishing blocklists, sanitize all inputs
- **Storage**: Efficient storage supporting 10M+ URLs per instance
- **Deployment**: Docker-based, single `docker-compose up` to run

## User Journeys

### Shorten a URL
1. User opens the web UI or calls the API
2. Pastes a long URL, optionally sets a custom alias and expiration
3. Receives a short URL immediately
4. Copies and shares the short URL

### View Analytics
1. User navigates to the analytics page for a specific short URL
2. Sees total clicks, click timeline chart, top referrers, and geographic breakdown
3. Filters by date range to analyze specific campaigns

## Success Metrics
- Average redirect latency < 50ms
- API response time < 200ms for all endpoints
- Zero data loss on click tracking
- Successful deployment in under 5 minutes via Docker

## Timeline
- **Week 1-2**: Core URL shortening and redirection
- **Week 3-4**: Click analytics and dashboard
- **Week 5**: Custom aliases, expiration, and polish
- **Week 6**: API documentation, Docker setup, and launch

## Open Questions
- Should we pre-validate destination URLs are reachable before shortening?
- What malware/phishing blocklist service to integrate?
- Should analytics data be retained indefinitely or have a TTL?
