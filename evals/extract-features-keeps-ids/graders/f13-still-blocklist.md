---
type: regex
pattern: '\|\s*F13\s*\|[^\n]*(malware|blocklist)'
flags: i
target: { source: file, path: FEATURES.md }
---
