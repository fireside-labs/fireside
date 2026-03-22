# Chat Tool Test Suite

> Copy-paste these prompts into the Fireside chat to manually verify each tool.
> Expected: Ember uses the tool and returns real results (not hallucinated).

## Results — March 21 2026 (Live test by Jordan)

| Test | Tool | Pass? | Notes |
|------|------|-------|-------|
| T1 | files_list | ✅ | Listed Desktop contents correctly |
| T2 | files_read | ✅ | Read test_from_ai.txt correctly |
| T3 | files_write | ✅ | Wrote tool_test.txt with timestamp |
| T4 | files_delete | ✅ | Deleted tool_test.txt, confirmed gone |
| T5 | web_search | ✅ | Returned real AI news results |
| T6 | browse_url | ✅ | Summarized Wikipedia AI article |
| T7 | store_memory | ✅ | Stored birthday as September 15th |
| T8 | recall_memory | ✅ | Recalled birthday *across conversations* |
| T9 | terminal_exec | ✅ | Ran echo + date, correct output |
| T10 | create_docx | ❌ | Got stuck listing user profile dir |
| T11 | create_xlsx | ⬜ | Not tested |
| T12 | create_pptx | ✅ | Created Demo.pptx with 3 slides |
| T13 | create_pipeline | ✅ | Researched AI agent trends (slow ~2min) |
| T14 | list_schedules | ❌ | Timed out twice |
| T15 | short-term memory | ✅ | Remembered context within conversation |
| T16 | context compaction | ✅ | Summarized full conversation accurately |

**Pass rate: 13/15 tested (87%)**

---

## Known Failures

### create_docx — stuck on path resolution
- Model tried to run `Get-ChildItem` to find username instead of using `~/Desktop/`
- Likely needs better system prompt guidance to use `C:\Users\Jorda\Desktop\` directly

### list_schedules — timeout
- Service timed out both attempts
- May be a backend plugin issue (scheduler not running or endpoint hanging)

---

## Remaining Bugs (Not Tool-related)

### 1. + button clears chat instead of saving
- Pressing + for new conversation clears the current one
- Previous conversation is lost — no sidebar persistence yet
- **Needs:** Conversation persistence layer (save to localStorage or backend API)

### 2. Tasks/Workflow tab still unstyled in Tauri exe
- Pipeline page CSS works on localhost:4001 but renders unstyled in Tauri webview
- @import fix applied, beforeBuildCommand now nukes cache
- **May need:** Investigation into Tauri CSP blocking the inline `<style>{pageCSS}</style>` pattern itself

### 3. Documents folder listing incomplete
- Model showed `/Users` instead of listing actual Documents folder
- Likely the model needs better path resolution guidance in system prompt

---

## Test Prompts

### T1: files_list
```
Show me what's on my Desktop
```

### T2: files_read
```
Read the file test_from_ai.txt on my Desktop
```

### T3: files_write
```
Write a file called tool_test.txt to my Desktop with the content: Tool test passed! Written at [current time].
```

### T4: files_delete
```
Delete tool_test.txt from my Desktop
```

### T5: web_search
```
Search the web for "latest AI news March 2026"
```

### T6: browse_url
```
Browse this URL and summarize it: https://en.wikipedia.org/wiki/Artificial_intelligence
```

### T7: store_memory
```
Remember that my birthday is September 15th
```

### T8: recall_memory (new conversation)
```
When is my birthday?
```

### T9: terminal_exec
```
Run this command for me: echo "Hello from the terminal!" && date /t
```

### T10: create_docx
```
Create a Word document on my Desktop called "Meeting Notes.docx" with a summary of today's tool testing session
```

### T11: create_xlsx
```
Create an Excel spreadsheet on my Desktop called "Budget.xlsx" with columns: Item, Cost, Category. Add 3 sample rows.
```

### T12: create_pptx
```
Create a PowerPoint presentation on my Desktop called "Demo.pptx" with 3 slides about AI companions
```

### T13: create_pipeline
```
Start a pipeline to research the latest trends in AI agents
```

### T14: list_schedules
```
Show me all my scheduled tasks
```

### T15: short-term memory
```
My dog's name is Max
```
Then: `What is my dog's name?`

### T16: context compaction
After 15+ messages: `Summarize what we've talked about so far`
