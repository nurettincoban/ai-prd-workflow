---
type: regex
pattern: '(edit|change|update)[^\n]{0,60}(destination|target URL|long URL)'
flags: i
target: { source: file, path: FEATURES.md }
---
