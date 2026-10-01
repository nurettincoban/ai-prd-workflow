---
type: regex
pattern: 'alias[\s\S]{0,300}(reserved|collid|collision|clash)|reserved (word|alias|path|route|name)'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
