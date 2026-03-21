# Chat Tool Test Suite

> Copy-paste these prompts into the Fireside chat to manually verify each tool.
> Expected: Ember uses the tool and returns real results (not hallucinated).

---

## ✅ Core File Tools

### T1: files_list
```
Show me what's on my Desktop
```
**Expected:** Lists actual files/folders from `C:\Users\Jorda\Desktop`

### T2: files_read
```
Read the file test_from_ai.txt on my Desktop
```
**Expected:** Shows actual file contents ("Hello from Ember! Today is March 21 2026.")

### T3: files_write
```
Write a file called tool_test.txt to my Desktop with the content: Tool test passed! Written at [current time].
```
**Expected:** File appears at `C:\Users\Jorda\Desktop\tool_test.txt`. Verify with File Explorer.

### T4: files_delete (with confirmation)
```
Delete tool_test.txt from my Desktop
```
**Expected:** Ember asks for confirmation first. After confirming, file is removed.

---

## 🔍 Web Tools

### T5: web_search
```
Search the web for "latest AI news March 2026"
```
**Expected:** Returns real search results with titles and URLs.

### T6: browse_url
```
Browse this URL and summarize it: https://en.wikipedia.org/wiki/Artificial_intelligence
```
**Expected:** Returns actual content summary from the Wikipedia page.

---

## 🧠 Memory Tools

### T7: store_memory
```
Remember that my birthday is September 15th
```
**Expected:** Ember acknowledges storing the memory.

### T8: recall_memory
```
When is my birthday?
```
**Expected:** Ember recalls "September 15th" from stored memory.

---

## 💻 Terminal Tool

### T9: terminal_exec
```
Run this command for me: echo "Hello from the terminal!" && date /t
```
**Expected:** Returns actual terminal output with the echo and current date.

---

## 📄 Document Creation Tools

### T10: create_docx
```
Create a Word document on my Desktop called "Meeting Notes.docx" with a summary of today's tool testing session
```
**Expected:** .docx file appears on Desktop, openable in Word.

### T11: create_xlsx
```
Create an Excel spreadsheet on my Desktop called "Budget.xlsx" with columns: Item, Cost, Category. Add 3 sample rows.
```
**Expected:** .xlsx file appears on Desktop, openable in Excel.

### T12: create_pptx
```
Create a PowerPoint presentation on my Desktop called "Demo.pptx" with 3 slides about AI companions
```
**Expected:** .pptx file appears on Desktop, openable in PowerPoint.

---

## ⚡ Pipeline Tools

### T13: create_pipeline
```
Start a pipeline to research the latest trends in AI agents
```
**Expected:** Pipeline starts, appears in the Tasks tab, WebSocket events flow.

### T14: list_schedules
```
Show me all my scheduled tasks
```
**Expected:** Lists schedules (or says "no schedules" if empty).

---

## 🔄 Conversation Memory Tests

### T15: Short-term memory (history)
```
My dog's name is Max
```
Then immediately:
```
What is my dog's name?
```
**Expected:** Ember says "Max" without needing to use recall_memory.

### T16: Context compaction
Have a conversation with 15+ messages, then:
```
Summarize what we've talked about so far
```
**Expected:** Ember recalls the key points from the conversation.

---

## 🔥 Edge Cases / Regression Tests

### E1: Relative path write
```
Write a file called edge_test.txt to ./Desktop with content: Relative path test
```
**Expected:** File appears at `C:\Users\Jorda\Desktop\edge_test.txt` (resolved from relative `./Desktop`)

### E2: Model doesn't refuse tools
```
What files are in my Documents folder?
```
**Expected:** Ember uses `files_list` — does NOT say "I don't have access to your file system"

### E3: Empty response after tool use
```
Create a file called silent_test.txt on my Desktop with content: This should not be silent
```
**Expected:** Ember confirms the write with a message (not blank response)

### E4: File write with tilde path
```
Write a file to ~/Desktop/tilde_test.txt with content: Tilde path resolved
```
**Expected:** File appears at `C:\Users\Jorda\Desktop\tilde_test.txt`

---

## 📋 Results Tracker

| Test | Tool | Pass? | Notes |
|------|------|-------|-------|
| T1 | files_list | ⬜ | |
| T2 | files_read | ⬜ | |
| T3 | files_write | ⬜ | |
| T4 | files_delete | ⬜ | |
| T5 | web_search | ⬜ | |
| T6 | browse_url | ⬜ | |
| T7 | store_memory | ⬜ | |
| T8 | recall_memory | ⬜ | |
| T9 | terminal_exec | ⬜ | |
| T10 | create_docx | ⬜ | |
| T11 | create_xlsx | ⬜ | |
| T12 | create_pptx | ⬜ | |
| T13 | create_pipeline | ⬜ | |
| T14 | list_schedules | ⬜ | |
| T15 | short-term memory | ⬜ | |
| T16 | context compaction | ⬜ | |
| E1 | relative path | ⬜ | |
| E2 | tool refusal | ⬜ | |
| E3 | empty response | ⬜ | |
| E4 | tilde path | ⬜ | |
