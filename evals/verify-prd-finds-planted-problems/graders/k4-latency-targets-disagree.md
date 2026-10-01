---
type: regex
pattern: '50 ?ms[\s\S]{0,400}(100 ?ms|p95)|(100 ?ms|p95)[\s\S]{0,400}50 ?ms'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
