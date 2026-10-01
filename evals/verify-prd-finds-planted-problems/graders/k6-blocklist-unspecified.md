---
type: regex
pattern: '(blocklist|block list|malware|phishing|safe browsing)[\s\S]{0,400}(provider|vendor|undecided|unspecified|unresolved|TBD|open question|re-?check|re-?scan|existing (links|URLs))'
flags: i
target: { source: file, path: PRD-REVIEW.md }
---
