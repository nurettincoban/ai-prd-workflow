# RFC-002: Click Analytics

## Summary
Add click tracking on every redirect and build analytics endpoints to query click data. This enables users to understand how their short URLs are performing.

**Complexity**: Medium
**Features**: F3 (Track clicks), F5 (Click count), F6 (Click timeline), F11 (Top referrers), F12 (Geographic breakdown)
**Builds upon**: RFC-001
**Required by**: None

## Technical Approach

### Database Schema
```sql
CREATE TABLE clicks (
  id SERIAL PRIMARY KEY,
  url_id INTEGER REFERENCES urls(id) ON DELETE CASCADE,
  clicked_at TIMESTAMP DEFAULT NOW(),
  referrer VARCHAR(2048),
  user_agent VARCHAR(1024),
  country_code CHAR(2)
);
CREATE INDEX idx_clicks_url_id ON clicks(url_id);
CREATE INDEX idx_clicks_clicked_at ON clicks(clicked_at);
```

### Click Tracking
- On redirect (GET /:code), asynchronously insert a click record
- Extract referrer from `Referer` header, user-agent from `User-Agent` header
- GeoIP lookup using a lightweight library (e.g., geoip-lite) for country code
- Click recording must not add > 10ms to redirect latency (use async fire-and-forget)

### Analytics API Endpoints
- `GET /api/urls/:code/analytics` - Full analytics for a URL
- `GET /api/urls/:code/analytics/timeline?period=day&from=&to=` - Click timeline
- `GET /api/urls/:code/analytics/referrers` - Top 10 referrers
- `GET /api/urls/:code/analytics/countries` - Click count by country

### Analytics Response Format
```json
{
  "data": {
    "totalClicks": 1234,
    "timeline": [{ "date": "2026-03-01", "clicks": 45 }],
    "topReferrers": [{ "referrer": "twitter.com", "clicks": 200 }],
    "countries": [{ "country": "US", "clicks": 500 }]
  }
}
```

## Acceptance Criteria
- [ ] Every redirect creates a click record with timestamp, referrer, user-agent, and country
- [ ] Click tracking adds < 10ms to redirect latency
- [ ] Analytics endpoint returns accurate total click count
- [ ] Timeline endpoint supports day/week/month grouping with date range filtering
- [ ] Referrers endpoint returns top 10 sorted by click count
- [ ] Countries endpoint returns click distribution by country code
- [ ] Integration tests for all analytics endpoints
