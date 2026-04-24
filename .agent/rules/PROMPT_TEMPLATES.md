---
trigger: always_on
---

# PROMPT_TEMPLATES.md

## 1. DEBUG PROMPT

Analyze this code and identify:

- timing issues
- focus issues
- race conditions

Do NOT implement yet.

---

## 2. REFACTOR PROMPT

Refactor this code:

- preserve behavior
- improve readability
- remove duplication
- add logging where needed

---

## 3. IMPLEMENTATION PROMPT

Objective:
[describe goal]

Context:
[current behavior]

Constraints:
- no fixed sleep
- must be thread-safe

Task:
[what to implement]

---

## 4. SAFE EDIT PROMPT

Rewrite this block so I can directly replace it.

Keep compatibility with existing flow.

---

## 5. AUTOMATION VALIDATION PROMPT

Analyze if this automation is reliable considering:

- focus issues
- popups
- timing
- retries

Suggest improvements.