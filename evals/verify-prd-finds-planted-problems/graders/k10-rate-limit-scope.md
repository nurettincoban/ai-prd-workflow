---
type: regex
pattern: 'rate[ -]?limit[\s\S]{0,400}(NAT|shared IP|prox(y|ies)|viral|popular link|corporate|IPv6)|(NAT|shared IP|prox(y|ies)|viral|IPv6)[\s\S]{0,400}rate[ -]?limit'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
