---
name: track
description: "Smart task routing -- route tasks to the right system based on category. Triggers: /track, add task, new task, track task."
---

# Track -- Smart Task Router

Route incoming tasks to the correct system based on their category.
This skill demonstrates the pattern of having multiple task backends
and routing to the right one based on task content analysis.

## Routing Rules

CUSTOMIZE: Define your task categories and destinations.

| Category | Destination | Tool/Method |
|----------|------------|-------------|
| Personal / household / content | Trello (or your personal task app) | `trello_create_card` or API call |
| Server / brain / infrastructure | dashboard.md (vault file) | `update_dashboard("add", ...)` |
| Work projects | Project management tool (Bitrix, Jira, etc.) | API call + vault backlog |

## How to Determine Category

Analyze the task description for keywords and context:

**Personal task manager (e.g., Trello):**
- Daily life tasks (buy, clean, call, schedule)
- Content creation (write post, record video, edit)
- Learning (read, watch course, study)
- Health/fitness (gym, workout, doctor)
- Social (meeting with friends, calls)
- Finance (pay, transfer)

**Dashboard / vault (server/infra):**
- Server maintenance (update server, configure nginx)
- Brain/vault tasks (add to vault, update skill, MCP)
- Automation (cron, script, bot)
- Development of personal tools

**Work project tool (e.g., Bitrix/Jira):**
- Keywords matching your work project names
- Work tasks: specs, PRD, meetings with colleagues, designs
- Mentions of clients, partners, team members

## Workflow

### Step 1: Parse Task

Extract from user input:
- Task title/description
- Optional: time estimate (fast/standard/serious/half_day/monster)
- Optional: deadline
- Optional: explicit destination ("to trello", "to dashboard", "to jira")

### Step 2: Determine Destination

If user specified destination explicitly -> use it.
Otherwise -> classify by keywords and context.

If ambiguous, ask the user:
```
Where should I put "task description"?
1. Personal tasks (Trello/Todoist/etc.)
2. Dashboard (server/infra)
3. Work project (Jira/Bitrix/etc.)
```

### Step 3: Create Task

**Personal task manager:**
```
trello_create_card(name="task", list_name="inbox", label_keys="standard")
```

**Dashboard:**
```
update_dashboard("add", "task description", project="brain")
```

**Work project tool:**
```
# Create in external tool via API
project_tool_create_task(title="task", responsible_id="YOUR_USER_ID")
```

**Write-through to vault (for work tasks):**
After creating a task in an external tool, ALWAYS update the vault backlog:
1. Read the current task file from vault
2. Add the new task to the appropriate section
3. Write the updated file back

This ensures your overview/aggregation skills can read from vault
without needing to query every external API.

### Step 4: Confirm

Tell user where the task was created:
```
Task created in [Trello/Dashboard/Jira]:
"Task title"
[label: standard] [deadline: DD.MM]
```

## Batch Mode

If user gives multiple tasks at once:
1. Parse all tasks
2. Classify each one
3. Show classification for approval
4. Create all after confirmation

## Time Label Shortcuts

CUSTOMIZE: Define your time estimate categories.

User can specify estimates inline:
- "quick" / "fast" -> fast (15-30 min)
- "standard" -> standard (45m-1.5h)
- "serious" / "big" -> serious (2-4h)
- "half day" -> half_day (5-7h)
- "monster" / "huge" -> monster (8+h)

## Important Notes

- Default destination for ambiguous tasks: **personal inbox** (safest default)
- Always confirm work tasks before creating (visible to team)
- For personal tasks: always create in inbox, user triages later
- For dashboard: specify project tag (brain, server, etc.)
