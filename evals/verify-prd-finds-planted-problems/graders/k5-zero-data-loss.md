---
type: regex
pattern: '(zero|no) data loss[\s\S]{0,400}(durab|queue|async|buffer|crash|lost|guarantee|unrealistic|unachievable)'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
