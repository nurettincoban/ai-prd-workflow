---
type: regex
pattern: '(?=[\s\S]*\|\s*F19\s*\|)(?=[\s\S]*\|\s*F20\s*\|)'
flags: i
target: { source: file, path: FEATURES.md }
---
