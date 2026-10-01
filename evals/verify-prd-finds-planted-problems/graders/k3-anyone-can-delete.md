---
type: regex
pattern: '(delet|list all|enumerat)[\s\S]{0,300}(anyone|any user|unauthenticated|without auth|no auth|ownership|owner)|(anyone|any user|unauthenticated|without auth|no auth|ownership)[\s\S]{0,300}(delet|list all|enumerat)'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
