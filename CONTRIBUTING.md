# 🤝 Contributing Guidelines

This project follows a **strict but fair development process** to ensure stability, clarity, and long-term maintainability 🧱

These rules exist to:
- 🚫 prevent merge conflicts
- 🛡️ protect the core system
- 🤝 allow parallel work without chaos

Please read this document fully before contributing.

---

## 🧠 1. Repository Philosophy

- ⭐ `main` is the **stable source of truth**
- 🧱 Stability > speed
- 🎯 Clear intent > clever code
- ✂️ Small, scoped changes > large dumps

This is an engineering project, not a scratchpad.

---

## 🌿 2. Branching Rules

### 🔒 Protected Branch
- `main` is protected
- ❌ No direct commits to `main`

### 🌱 Feature Branches
All work must be done in a feature branch.

**Branch naming convention:**
```
feature/<your-name>/<short-description>
```

**Examples:**
```
feature/mansi/ui-shell
feature/abhey/reasoning-loop
```

### ⏳ Branch Discipline
- Branches should be **short-lived**
- ☝️ One branch = one task
- 🔄 Keep branches reasonably up to date with `main`

Long-running branches increase merge risk and will be discouraged.

---

## 🗂️ 3. File Ownership & Scope

- Each contributor will be assigned **specific files or modules**
- You are expected to work **primarily within your assigned scope**
- You may modify other files **only if required for integration or interfaces**

### ⚠️ Important Rules
- 🚫 Do not refactor unrelated code
- 🚫 Do not change system-wide behavior without discussion
- 📌 Any cross-module changes **must be explicitly stated in the PR**

Ownership is about responsibility, not isolation.

---

## 🔄 4. Syncing With `main`

- ✅ You may pull or rebase from `main` to stay updated
- ❌ Do not merge `main` into your branch without informing the maintainer
- 🗣️ If upstream changes affect your work, communicate early

Silent merges are not acceptable.

---

## 🔍 5. Pull Requests (PRs)

All changes must go through a Pull Request.

A PR **must**:
- 🧪 Build successfully
- 🧯 Not break unrelated functionality
- 🎯 Be scoped to the assigned task
- ✍️ Contain meaningful, readable commits

### 📝 PR Description Should Include:
- What was changed
- Why it was changed
- Any files touched outside assigned scope

PRs that introduce instability, scope creep, or unclear intent will be rejected ❌

---

## 🧾 6. Commit Message Guidelines

Commit messages should describe **intent**, not vague outcomes.

### ❌ Bad Examples
```
fixed stuff
changes
update
```


### ✅ Good Examples
```
add query rewriting module
refactor memory interface for clarity
add UI skeleton for agent input
```


Prefer:
- 🔹 small commits
- 🔹 clear intent
- 🔹 logical progression

---

## 🛠️ 7. Code Quality Expectations

- ✨ Write readable, maintainable code
- 🧠 Avoid unnecessary abstractions
- 📦 Do not introduce new dependencies without discussion
- 🧩 Follow existing project structure and patterns

If unsure about an approach, **ask before implementing** 🙋

---

## 👀 8. Reviews & Authority

- 🔐 All PRs require maintainer approval
- 🧭 Final responsibility for system stability lies with the maintainer
- 💬 Feedback will be given when needed
- 🛡️ Stability always takes priority over speed or novelty

This process exists to protect **everyone’s work**, including yours.

---

## 💬 9. Communication

- 🕑 Ask questions early
- ⚠️ Raise concerns before merging
- 🚫 No silent assumptions
- 🚫 No surprise changes

Clear communication prevents wasted effort.

---

## ✅ Final Note

These rules are not meant to slow development.  
They exist to ensure that the project can grow **without collapsing under its own complexity** 🧠🏗️

Thank you for respecting the process and contributing responsibly 🙌