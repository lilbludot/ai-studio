# LLM Workspace

An LLM workspace - chat + editor with file tools.

## Setup

```bash
export CLAUDE_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
python main.py
then open http://localhost:7860 in your browser
```

## What It Does

- Chat with Claude/GPT while editing documents
- LLMs can read/write files in ~/iCloud Drive/ClaudeProjects/
- Auto-saves versions in .versions folders
- LLMs can read/write files in your iCloud Drive under `ClaudeProjects/` (or another configured directory)
- Tracks costs and tokens

## File Tools the LLMs Can Use

- `list_files` - browse directories
- `read_file` - read without showing in editor  
- `open_and_display_file` - open in editor
- `create_file` - make new files
- `save_editor_to_file` - save current editor content
- `get_editor_content` - see what's in editor
- `edit_text_in_editor` - update editor content

## TODO

- [ ] iCloud Drive integration 
- [ ] Tagged versions for milestones
- [ ] Keyboard shortcuts (Ctrl+S, etc)
- [ ] Auto-save with debouncing
- [ ] Better error messages

## Notes

- Version cleanup keeps: 24h all, daily for week, weekly for month
- Database is in data/ai_studio.db
- Logs in logs/ai_studio.log
