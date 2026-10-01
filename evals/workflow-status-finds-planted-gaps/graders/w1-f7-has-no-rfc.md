---
type: regex
pattern: 'F7[\s\S]{0,300}(no RFC|not (assigned|covered|included|mapped)|unassigned|missing|orphan|uncovered)|(no RFC|unassigned|not covered|uncovered|missing)[\s\S]{0,300}F7\b'
flags: i
target: last_message
---
