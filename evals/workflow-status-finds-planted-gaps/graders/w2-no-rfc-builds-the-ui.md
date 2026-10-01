---
type: regex
pattern: '(dashboard|front-?end|React|\bUI\b)[\s\S]{0,300}(no RFC|not (covered|planned|assigned)|missing|absent|unplanned)|(no RFC|not covered|missing)[\s\S]{0,300}(dashboard|front-?end|\bUI\b)'
flags: i
target: last_message
---
