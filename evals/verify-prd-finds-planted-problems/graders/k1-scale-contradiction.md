---
type: regex
pattern: '10,?000[\s\S]{0,600}10 ?(M\b|million)|10 ?(M\b|million)[\s\S]{0,600}10,?000'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
