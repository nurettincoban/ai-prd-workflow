---
type: regex
pattern: '(99\.9|uptime|availability)[\s\S]{0,400}(single|one)[ -](instance|node|server|host|container)|(single|one)[ -](instance|node|server|host|container)[\s\S]{0,400}(99\.9|uptime|availability)'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
