---
type: regex
pattern: '\|\s*F1\s*\|[^\n]*(Create|auto-generated)'
flags: i
target: { source: file, path: FEATURES.md }
---
