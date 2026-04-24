---
trigger: always_on
---

# AUTOMATION_PATTERNS.md

## 1. RETRY PATTERN

Always prefer:

- attempt action
- validate result
- retry if needed

Never blindly repeat actions.

---

## 2. FOCUS CONTROL

Always consider:

- active window
- lost focus
- popup interference

Validate before sending input.

---

## 3. POPUP HANDLING

- detect popup
- handle safely
- confirm closure
- restore focus

---

## 4. TIMING STRATEGY

Avoid:

- fixed sleep for critical logic

Prefer:

- conditional wait
- state-based progression

---

## 5. THREAD SAFETY

Always respect:

- stop_event
- pause_event

Allow safe interruption.

---

## 6. COUNTDOWN LOGIC

If loop has interval:

- allow restart during countdown
- do not block user interaction

---

## 7. VALIDATION STRATEGY

After every critical action:

- confirm expected state
- retry if necessary