# RFC-011: OpenAPI, Swagger UI and API Completeness

**Features**: F21, F23, F24, F32
**Depends on**: RFC-002, RFC-004, RFC-007, RFC-008, RFC-010
**Rules**: API-1, API-2, API-3, API-4, API-8, ARCH-4, ARCH-8, SEC-9, SEC-10, TEST-5, TEST-9, TEST-2, COMP-2, TEST-4, STACK-4, API-7
**Complexity**: Medium

## Summary

Makes the API's contract explicit and checked. The OpenAPI document is generated from the routes' TypeBox schemas by `@fastify/swagger` (API-2, F23) and served at `/docs/json`; Swagger UI renders it at `/docs` (F24). A contract test fails if any `/api/v1/` route or declared status is missing from the document (TEST-5), and a parity test fails if any web-UI operation lacks an API equivalent (F21, ARCH-4). It also adds F32's remaining scenario -- management and analytics endpoints p95 < 200 ms (NFR-8) -- to RFC-004's harness.

## Technical Approach

### OpenAPI generation (F23)

- Register `@fastify/swagger` in `src/app.ts` **before** any route (the plugin collects schemas as routes register), with `openapi: { openapi: "3.1.0", info: { title: "LinkSnip API", version: <package.json version> }, servers: [{ url: "<scheme>://<public host>" }], components: { securitySchemes: { managementToken: { type: "http", scheme: "bearer" }, adminToken: { type: "http", scheme: "bearer" } } } }`. Only `/api/v1/` routes are included (`hideUntagged` or a `transform` that drops non-API routes; the redirect, pages, `/health` and `/docs` are not part of the API contract -- assumption).
- Each API route adds `tags`, `summary`, `description`, and `security` (`managementToken` on DELETE, `adminToken` on list, none elsewhere). TypeBox schemas from earlier RFCs are reused. The shared error schema is `Type.Object({...}, { $id: "ErrorBody" })` in `src/errors.ts`. It is registered once with `app.addSchema(ErrorBody)`, and every 4xx and 5xx response references it as `Type.Ref(ErrorBody)` (API-3). @fastify/swagger emits schemas added with `addSchema` as `components.schemas.ErrorBody`, and the contract test checks for it.
- Descriptions state the behaviors a client must know: creation is not idempotent (RFC-002); `blocklistStatus` meanings (API-6); the token is returned once; analytics exclude bots, are UTC, and ranges are inclusive; 429 and `Retry-After` on every `/api/v1/` route (RFC-010 -- each route declares 429).
- `src/routes/api/` therefore gains: 429 response schemas on every route, and on POST `/api/v1/urls` the 400 codes enumerated in the description.

### Swagger UI (F24)

- `@fastify/swagger-ui` at `routePrefix: "/docs"`, spec at `/docs/json` (and `/docs/yaml`). `docs` is already reserved (RFC-001).
- CSP (decided after the cold read): `'unsafe-inline'` is never used, on any route. Swagger UI's assets are served from the instance (`/docs/static/...`). If the pinned version's HTML needs an inline script, the plugin's `staticCSP` option adds that script's **hash** to `script-src`, on `/docs` responses only. SEC-10 literally allows only `'self'`, so even a hash is a deviation, and RFCS.md **flags SEC-10** to allow hashes on `/docs` (assumption until then). If no inline script is needed, no hash is added.
- Not rate limited (SEC-9).

### Contract test (TEST-5)

Route list (cold read: Fastify has no public list of registered routes): `buildApp` adds an `onRoute` hook that pushes `{ method, url, schema, config }` into an array, exposed through the decorator `app.routeList`. Automatic HEAD routes (`routeOptions.exposeHeadRoute`, or HEAD entries whose GET twin exists) are marked and excluded from the contract.

Every route declares `config.kind`, one of `"api" | "web" | "redirect" | "system"`. `system` covers `/health`, `/static/*` and `/docs*`. A test fails if any route has no `kind`.

```
test/integration/openapi-contract.test.ts:
  app = buildApp(fakes); await app.ready()
  spec = (await app.inject("/docs/json")).json()
  for each route in app's registered routes with url starting "/api/v1/":
     path = toOpenApiPath(route.url)                  # ":code" → "{code}"
     assert spec.paths[path][route.method.toLowerCase()] exists
     for each status in route.schema.response: assert spec.paths[path][method].responses[status] exists
  for each path+method in spec: assert a registered route exists (no stale entries)
  validate spec against the OpenAPI 3.1 schema (a JSON-schema check with the schema file vendored in test/fixtures)
```

The test also makes real requests and validates each response body against the documented schema for its status. For each operation it covers the success case and every documented error status it can trigger without a third party: create gives 201, 400 and 409; delete gives 204, 403 and 404; list gives 200, 400 and 403; analytics gives 200, 400 and 404. Behavior and spec therefore cannot disagree on error shapes either (F23 assumption).

Schema validation needs a JSON Schema 2020-12 validator, which the RULES stack does not list. Following STACK-4, this RFC adds `ajv` (it is already in Fastify's tree) as an exact-pinned devDependency, uses its 2020-12 build, verifies the version against the npm registry when implementing, and adds the row to the RULES Technology Stack table in the same change. The OpenAPI 3.1 meta-schema is vendored in `test/fixtures/`.

### API parity (F21)

The full API surface after this RFC:

| Operation | Method and path | RFC |
|---|---|---|
| Create (code, alias, expiry) | `POST /api/v1/urls` | RFC-002 |
| Delete | `DELETE /api/v1/urls/{code}` | RFC-008 |
| List (operator) | `GET /api/v1/urls` | RFC-008 |
| Analytics (total, timeline, referrers, countries, range) | `GET /api/v1/urls/{code}/analytics` | RFC-007 |

Parity is declared on the routes themselves, not in a table inside the test, so the test cannot pass by construction. Every `kind: "web"` route that performs an operation declares `config.apiEquivalent`, e.g. `"POST /api/v1/urls"` on `POST /shorten` and `"GET /api/v1/urls/{code}/analytics"` on `GET /analytics/:code`. `GET /` is a plain form page and declares `apiEquivalent: null` with a reason string. `test/integration/api-parity.test.ts` fails in either case:
- a `web` route has no `apiEquivalent` key, or
- its value does not name a registered `kind: "api"` route (FR-14: everything the UI does, the API does).

API-1: every `kind: "api"` route must start with `/api/v1/`, and the only `system` routes that return JSON are `/health` and `/docs/json`. A test enumerates `app.routeList` for both conditions.

### API latency scenario (F32 remainder, NFR-8)

- `load/api.js`: k6 `constant-arrival-rate` at 50 requests/s for 5 minutes, after a 30 s warm-up excluded from the figures (assumption: NFR-8 states no rate; 50/s is well above a self-hosted instance's expected API traffic and is recorded in the result). The mix:
  - 40% analytics, for a random code from RFC-004's `load/data/active-codes.txt`, default range
  - 30% create
  - 20% list with the admin token: the first page, then following `nextCursor` for up to 4 more pages (keyset cursors cannot jump to a random page, API-7)
  - 10% delete, of links created earlier in this run, using the tokens their create responses returned
- Every request is valid, so **no 4xx is expected**. `http_req_failed` must be 0, with every non-2xx counting as a failure.
- Each operation is tagged `op:create|list|analytics|delete`.
- Latency is judged server-side, as in RFC-004: `load/server-latency.ts` computes p95 per route from `request_completed` logs and fails unless **each** of the four API routes has p95 < 200 ms (NFR-8 says "all endpoints"). k6's per-op client-side p95 is reported.
- Limits are inert: `load/compose.load.yaml` sets `LINKSNIP_API_RATE_LIMIT=1000000` (RFC-010).
- It runs against the RFC-004 seed (10M URLs) after a redirect run has written click data, with the no-op `UrlChecker` (third-party latency excluded, see RFC-005) and rate limits made inert in `load/compose.load.yaml`.
- `load/server-latency.ts` (RFC-004) gains per-route API summaries; the combined release result is committed under `load/results/` (TEST-9).
- NFR-2 (99.9%): not load-testable; the README statement is written in RFC-012 (F32's last criterion).

### Versioning (API-8)

The OpenAPI `info.version` tracks the app version, and the path prefix `/api/v1/` is the compatibility contract. A snapshot of the generated spec is committed as `docs/openapi.json`. `test/integration/api-compat.test.ts` resolves every `$ref` in both documents, ignores `servers` and `info.version`, and **fails** on any breaking difference:
- an operation removed
- a response status removed
- a response property removed or renamed, or its `type` changed
- a response `enum` value removed
- a request property becoming required, or a new required request property
- a request `enum` value removed, or a request constraint tightened (`maxLength`, `pattern`, `minimum`/`maximum`)

Additive differences, such as a new operation, a new optional property or a new status, do not fail the test. The test prints them and tells the developer to run `npm run openapi:snapshot`, which rewrites `docs/openapi.json` for review in the same change. This is a mechanical guard for API-8 (assumption).

## File Structure

```
src/app.ts                                   (swagger + swagger-ui registration)
src/routes/api/*.ts                          (tags, summaries, security, 429 schemas)
src/routes/**/*.ts                           (config.kind on every route; apiEquivalent on web routes)
src/app.ts                                   (onRoute hook, app.routeList decorator)
src/errors.ts                                (shared ErrorBody TypeBox schema exported beside the code catalog)
docs/openapi.json                            (committed snapshot)
test/integration/openapi-contract.test.ts  test/integration/api-parity.test.ts  test/integration/api-compat.test.ts
test/e2e/docs.spec.ts
package.json                                 (ajv devDependency, openapi:snapshot script)
RULES.md                                     (Technology Stack row for ajv, per STACK-4)
test/fixtures/openapi-3.1-schema.json
load/api.js  load/server-latency.ts (extended)  load/README.md (extended)
load/results/<run>/RESULT.md
```

## Implementation Considerations

- **Swagger ordering**: register `@fastify/swagger` before routes or the spec is empty -- the contract test catches this.
- **Testing**: the contract test is the guard against hand-written spec drift (API-2 forbids hand-writing it).
- **Compatibility**: the snapshot test makes accidental breaking changes visible in review.
- **Third-party**: `@fastify/swagger` and `@fastify/swagger-ui` (RULES stack), plus `ajv` as a new devDependency (STACK-4, above). The OpenAPI 3.1 JSON schema file is vendored for offline tests (TEST-4).

## Acceptance Criteria

**F23 -- OpenAPI**
1. `GET /docs/json` returns an OpenAPI 3.1 document generated from route schemas (no hand-written spec file is loaded), valid against the vendored OpenAPI 3.1 schema (API-2).
2. The document contains exactly the four operations in the parity table, each with request schemas, every response status the route can return (including 429 and the shared `ErrorBody` for 4xx/5xx), tags, summary, and `security` for the two token-protected operations.
3. `test/integration/openapi-contract.test.ts` fails if a registered `/api/v1/` route or a declared status is missing from the document, if the document lists an operation with no route, or if a real response does not validate against its documented schema (TEST-5).
4. Operation descriptions state: creation is not idempotent; the management token is shown once; `blocklistStatus` values; analytics are UTC, inclusive, bots excluded; 429 with `Retry-After`.

**F24 -- Swagger UI**
5. `test/e2e/docs.spec.ts` (Chromium) opens `/docs` and asserts that Swagger UI lists exactly the four operations, with no CSP violation reported in the console. Every asset is requested from the instance's origin. No response on any route carries `'unsafe-inline'` in its CSP. `/docs` is not rate limited (SEC-9, SEC-10).

**F21 -- API completeness**
6. `test/integration/api-parity.test.ts` fails if any route lacks `config.kind`, if a `web` route lacks `apiEquivalent`, or if an `apiEquivalent` does not name a registered `api` route. A test-only route registered without `apiEquivalent` makes it fail (FR-14, ARCH-4).
7. Every `kind: "api"` route starts with `/api/v1/`, and the only `system` routes whose responses are `application/json` are `/health` and `/docs/json`. Both are checked by enumerating `app.routeList` and injecting each GET `system` route (API-1).
8. `docs/openapi.json` is committed. `test/integration/api-compat.test.ts` fails for each breaking difference listed in Versioning, each exercised by a fixture pair, and passes, while printing them, for additive differences (API-8).

**F32 -- API latency (NFR-8)**
9. `load/api.js` runs the documented mix at 50 requests/s for 5 minutes against the 10M-URL seed, and fails on any non-2xx response. `load/server-latency.ts` fails unless the server-side p95 is under 200 ms for **each** of create, delete, list and analytics separately (NFR-8).
10. Release checklist step, done by hand: the release run on RFC-004's reference host, with a separate k6 machine, is committed under `load/results/<YYYY-MM-DD>-<git short sha>/` alongside a reference-host verdict run of RFC-004's redirect and durability scenarios for the same commit. `RESULT.md` states the rate, mix, checker (no-op) and hardware (TEST-9).
11. Tests are named `"F21: ..."`, `"F23: ..."`, `"F24: ..."`, `"F32: ..."` (TEST-2); the 50 requests/s rate, API-only spec scope and snapshot guard carry comments citing this RFC (COMP-2).
