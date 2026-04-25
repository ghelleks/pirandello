# SDD Scenarios: `add-role` Skill

**Companion spec:** `docs/specs/add-role-skill/spec.md`  
**Date:** 2026-04-23

---

## Use Cases

### 1. New consulting role — all credentials provided

A user runs `masks add-role consulting --interactive`. The directory has been created, `.env.example` copied to `consulting/.env`, and hooks installed. The skill now conducts the conversational credential collection. The user has all credentials ready and provides values for every key.

Questions the proposal must answer:
- Does the skill ask about every key in `.env.example`, one at a time?
- Does each question name the key in plain language and explain what it is and where to find it?
- Does it confirm each provided value with a human-readable message before moving to the next key?
- Does it write all provided values to `consulting/.env`?
- Does the end summary list which keys were set, which were skipped, and the remote status?

Metric cross-references: M-01, M-02, M-04, M-06, M-08

---

### 2. User skips multiple credentials

A user is setting up a new personal board seat Role. Several keys in `.env.example` (e.g., `WORKBOARD_API_KEY`, `GITLAB_TOKEN`) are not relevant for this Role. The user skips them.

Questions the proposal must answer:
- Is each skipped key still written to the `.env` file as an empty value (not omitted)?
- Does the skill confirm that each skipped key has been recorded ("Got it — I've left that blank for now")?
- Does skipping a key allow the skill to proceed to the next key without blocking or re-asking?
- Does the end summary list the skipped keys explicitly?

Metric cross-references: M-03, M-06, M-08

---

### 3. User unfamiliar with a credential

During key collection, the skill asks about `MCP_MEMORY_DB_PATH`. The user responds "I don't know where to find that."

Questions the proposal must answer:
- Does the skill offer a plain-language hint (e.g., "This is the file path for the search database that Pirandello uses — you'd find it in the setup output when you first configured the system") before re-asking?
- Does it avoid jargon (`SQLite`, `sqlite-vec`) unless the hint needs it, and explain any unavoidable jargon in simple terms?
- Does it wait for the user's input after giving the hint, rather than moving on?

Metric cross-references: M-02

---

### 4. User provides a git remote

The user provides a git remote URL (`git@gitlab.company.com:user/board.git`) for the new Role.

Questions the proposal must answer:
- Does the skill write the remote to the Role's git config using `git remote add origin <url>`?
- Does the skill confirm the remote was wired: "Got it — I've set the git remote for this role."?
- Is the remote question asked after credential collection, or at a defined point in the flow?

Metric cross-references: M-07, M-08

---

### 5. User skips the git remote question

When asked for a git remote, the user says "I don't have one yet" or "skip."

Questions the proposal must answer:
- Does the skill accept the skip without retrying the question or expressing concern?
- Does it move forward to signal source collection without blocking?
- Does the end summary note that no remote was configured?
- Is the user's ability to add a remote later acknowledged?

Metric cross-references: M-07, M-08

---

### 6. Signal source collection

After credentials, the skill asks "What signal sources should this role monitor?" The user lists three sources (a specific calendar, a Slack workspace, and an RSS feed).

Questions the proposal must answer:
- Does the skill collect this information in the conversation?
- What does the proposal do with this input — write it to OODA.md's Signal Sources section, return structured data to `masks add-role` for writing, or something else?
- Is the resulting signal source list stored in a way that `masks run` can use it?

Metric cross-references: M-08 (end summary must include remote status; implies signal sources are also part of the outcome)

---

### 7. Skill invoked directly (not via `masks add-role --interactive`)

A user is inside a session and says "add a new role" without using the CLI. The skill is invoked directly.

Questions the proposal must answer:
- Does the skill ask for the Role name at the start of the conversation (since `masks add-role` normally provides it)?
- Does it handle the case where `.env.example` may need to be read directly from `pirandello/`?
- Does the skill's open decisions section address this direct-invocation path?

Metric cross-references: M-01, M-02 (all keys covered, plain-language questions)

---

## Stress Tests

**T1 Every key in `.env.example` is asked about.**  
The skill asks a question for every key in `.env.example`, including those the user is likely to skip. No key is silently omitted.  
Pass: the count of questions asked equals the count of keys in `.env.example`; any key not asked about fails this test.

**T2 Each question is in plain language.**  
Every key question names the key (in human-readable form) and explains what it is without assuming the user knows what it is.  
Pass: reviewing the proposal's question templates, each includes a non-technical explanation; questions that only show the raw key name (e.g., "What is your `GMAIL_REFRESH_TOKEN`?") without explanation fail.

**T3 Skipped keys are written as empty strings in `.env`.**  
After the skill completes, a key the user skipped appears in `consulting/.env` as `KEY_NAME=` (empty value), not absent from the file.  
Pass: `grep "SKIPPED_KEY" consulting/.env` returns one line with an empty value, not zero results.

**T4 Only one key is presented per turn.**  
No single turn in the credential collection presents multiple keys as a list or asks two questions.  
Pass: reviewing the dialogue design, each turn ends with a question about a single key; bulleted lists of keys fail this test.

**T5 The skill never shows `.env` or `.env.example` file contents to the user.**  
The raw key list, file paths, and `.env` file contents are never shown in the conversation.  
Pass: the proposal's dialogue templates never render the `.env` or `.env.example` file as text output to the user.

**T6 Confirmation after each key.**  
After each key is written (or skipped), the skill confirms with a human-readable message.  
Pass: the proposal's dialogue design includes a confirmation turn after every key, including skipped ones.

**T7 Git remote question allows a clean skip.**  
The user can answer "no" or "skip" to the remote question without the skill re-asking or blocking.  
Pass: the proposal's dialogue flow after a remote skip proceeds to signal sources or end-of-skill without re-asking.

**T8 End summary is always produced.**  
After all keys and the remote question, the skill produces a summary listing: set keys, skipped keys, and remote status.  
Pass: the end of every skill run (regardless of how many keys were skipped or whether a remote was configured) includes a summary.

---

## Anti-Pattern Regression Signals

**Keys silently skipped without asking.** The skill omits keys it judges to be "irrelevant" for the Role type (e.g., skipping `WORKBOARD_API_KEY` for a personal Role). Symptom: `.env` is shorter than `.env.example`; adding that tool to the Role later requires manually editing the file. Indicates: filtering of "relevant" keys before presenting them. Maps to: M-01.

**Multiple keys in a single turn.** The skill presents "Now I need a few credentials — your Gmail refresh token, your Google Calendar ID, and your Todoist API key." Symptom: user gives rushed or partial answers; some keys are missed; the `.env` file is incomplete. Indicates: batch credential collection instead of one-at-a-time flow. Maps to: M-04.

**`.env` file exposed during confirmation.** After writing a key, the skill shows the user the current state of the `.env` file: "Here's what your `.env` looks like now: `GMAIL_REFRESH_TOKEN=ya29.xxx`." Symptom: credentials are visible in the chat transcript; security and spec constraint violated. Indicates: M-05 violation (file must not be shown). Maps to: M-05.

**Git remote question blocks on failure.** If the user provides a remote URL and `git remote add origin` fails (e.g., the URL has a typo), the skill retries indefinitely or refuses to continue. Symptom: onboarding stalls when a remote is unreachable; user cannot complete role setup without fixing the remote. Indicates: remote configuration treated as a required step rather than an optional one. Maps to: M-07.

**End summary absent after partial completion.** If the user skips the git remote question, the skill ends without producing a summary — as if the lack of a remote means nothing to report. Symptom: user has no record of which credentials were set and which were skipped; must re-run the skill to find out. Indicates: end summary only triggered by complete credential collection, not always. Maps to: M-08.
