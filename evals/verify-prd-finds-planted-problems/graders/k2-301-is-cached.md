---
type: regex
pattern: '301[\s\S]{0,400}(cach|browser)|(cach|browser)[\s\S]{0,400}301'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
