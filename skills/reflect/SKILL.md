---
name: reflect
description: "Daily reflection -- what was done, depth of work, analysis. Triggers: /reflect, reflection, daily review, how was my day, what did I do today."
---

# Daily Reflection

A meaningful daily reflection -- not just a task list, but analysis of what happened,
the volume of work behind it, what went well and what didn't.

**Principle:** Two data layers -- task delta (what moved) + work narrative (what actually happened).
Without the second layer, reflections will be dry and incomplete.

**Chain:** `/reflect` (day) -> `/retro` (week) -> `/monthly-review` (month)

---

## Step 1: Get Today's Date

```
get_today()  -- MANDATORY first call, for date filtering
```

Remember today's date in YYYY-MM-DD format (for filtering) and DD.MM (for display).

---

## Step 2: Gather Task Delta (Layer 1)

Read from all your task sources -- with a **backward filter**: what CHANGED/CLOSED today.

CUSTOMIZE: Replace these with your actual task sources.

### Parallel batch 1 (task manager + calendar):

```
trello_list_cards(list_name="done")              -- what was closed
trello_list_cards(list_name="today")             -- what's still in today (planned but not done)
list_calendar_events()                            -- today's events
```

### Parallel batch 2 (vault sources):

```
read_vault("work/project/tasks/TASKS.md")        -- completed items with today's date
read_vault("dashboard.md")                        -- items with today's date
```

### Backward filter logic:

| Source | What to look for in reflection |
|--------|-------------------------------|
| **Task manager done** | Cards/tasks with activity date = today. Done list may be cumulative -- ALWAYS filter by date! |
| **Task manager today** | What's left = what was planned but NOT done |
| **Work tasks** | Rows marked done with today's date |
| **Dashboard** | Active tasks with today's date. Completed with today's date |
| **Calendar** | Events on today's date (meetings, deadlines) |

---

## Step 3: Gather Work Narrative (Layer 2)

Session notes = depth of work. Task list shows WHAT, session notes show HOW and HOW MUCH.

### Read session index:

```
read_vault("conversations/CONVERSATIONS.md")
```

### Filter by today's date:

Find all entries in CONVERSATIONS.md containing today's date.
Extract paths to session files.

### Read each session file:

For each session from today -- read via `read_vault()`.
Extract:
- **"What was done"** -- concrete actions
- **"Decisions made"** -- decisions taken
- **Tags** -- domains (project-a, brain, job-search, content, etc.)

**IMPORTANT:** Read session notes in parallel (up to 5 at a time).

---

## Step 4: Analyze & Synthesize (Layer 3)

### 4.1 Group by domain

Combine data from Layer 1 (tasks) and Layer 2 (sessions) into domains:

CUSTOMIZE: Define your domains based on your life/work areas.

- **Work Project** -- work tasks + calendar events + sessions tagged with project
- **Job Search** -- job search changes + sessions tagged job-search
- **Server/Brain** -- dashboard items + sessions tagged brain/server
- **Content** -- content plan + content tasks + sessions tagged content
- **Personal** -- personal tasks (gym, chores, etc.)
- **Other** -- everything that doesn't fit above

### 4.2 For each domain:

1. **What was done** -- tasks + depth from session notes
2. **Key decisions** -- from "Decisions made" in sessions
3. **Work volume** -- time labels from task manager + number of sessions

### 4.3 Meta-analysis:

- **Plan vs reality** -- what was in today list this morning vs what actually closed
- **Unplanned** -- tasks that appeared during the day (not in morning plan)
- **Missed** -- what's still in today / fail items / overdue
- **Balance** -- which domains dominated, what didn't get attention
- **Energy** -- hours (by task labels), session count, intensity

---

## Step 5: Present Reflection

### Format:

```
Reflection for DD.MM (day of week)

OVERVIEW
-- Tasks closed: N (from task manager) + N (from work/dashboard)
-- Work sessions: N
-- Estimated time: ~X.X hours (by task labels)
-- Dominant domain: [domain]

[DOMAIN 1]
[Tasks + depth from sessions. NOT just a list -- describe what actually happened]

[DOMAIN 2]
[What happened, who you talked to, what decisions were made]

...

WINS
-- Top achievements of the day (2-3 items)

MISSED / DIDN'T FIT
-- What's left + why (conscious choice or lack of time?)

KEY DECISIONS
-- Decisions from sessions that affect the future

TOMORROW
-- What's already in today list (from Layer 1)
-- Leftovers from today (overdue, fail)
-- Recommendation (what's higher priority, what to focus on)
```

### Style:

- **Not a dry list** -- narrative, as if talking to a person
- **Depth** -- for each domain, not "task closed" but what was behind it
- **Honesty** -- if the day was overloaded, say it. If something was missed, don't hide it
- **Specifics** -- numbers, names, decisions. Not "worked on project", but "had a call with Alex, reviewed 5 screens, assigned 4 tasks"

---

## Step 6 (optional): Tomorrow Preview

If user asks about tomorrow ("what's tomorrow?", "plans for tomorrow"):

```
trello_list_cards(list_name="today")    -- current today list = tomorrow's plan
list_calendar_events()                   -- tomorrow's events
read_vault("work/project/tasks/TASKS.md")  -- deadlines for tomorrow
```

Show: what's already planned + what needs to be added (leftovers, overdue).

---

## Important Rules

1. **get_today() FIRST** -- always, no exceptions
2. **Session notes = mandatory layer** -- without them, reflection will be superficial
3. **Task manager done = key source, but filter by date!** -- done list may be cumulative. Each card has a date. Take ONLY cards with today's date
4. **User can narrow scope** -- "only work tasks", "only after 3pm" -> filter accordingly
5. **Ask user** if clarifications needed (which tasks are today's, context on fail items)
6. **AUTO-SAVE** -- after presenting reflection, ALWAYS save to vault: `write_vault("retro/daily/YYYY-MM-DD.md", ...)` with tags `retro,daily` + day's domains. Don't ask -- save automatically
7. **Chain with /retro** -- daily reflection feeds weekly retro. If end of week, suggest "/retro?"

---

## Related Skills

- `/overview` -- forward-looking task aggregator (what to do). Reflect = backward-looking (what was done)
- `/retro` -- weekly retrospective. Uses archived done list for week stats
- `/monthly-review` -- monthly aggregation of retros
- `/track` -- task routing (write). Reflect is read-only analysis
