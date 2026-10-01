---
type: regex
pattern: 'RFC-003[\s\S]{0,300}(depend|predecessor|requires|needs|undeclared)[\s\S]{0,300}RFC-002|RFC-002[\s\S]{0,300}(before|predecessor|dependency of)[\s\S]{0,200}RFC-003'
flags: i
target: last_message
---
