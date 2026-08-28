# Tools Catalog

## Core Tools

### ShellTool
- **Module**: tools/shell_tool.py
- **Description**: Execute shell commands safely
- **Input**: `{"command": "string"}`
- **Output**: stdout, stderr, return code

### FileTool
- **Module**: tools/file_tool.py
- **Description**: Read, write, append, list, search files
- **Operations**: read, write, append, list, search, delete

### LLMTool
- **Module**: tools/llm_tool.py
- **Description**: Call NVIDIA LLM API with any prompt
- **Models**: step-3.5-flash, kimi-k2-instruct-0905

### MemoryTool
- **Module**: tools/memory_tool.py
- **Description**: Read/write/search agent memory
- **Operations**: read, write, search, clear_section

### SwarmTool
- **Module**: tools/swarm_tool.py
- **Description**: Spawn parallel sub-agents for distributed tasks
- **Operations**: spawn, broadcast, gather, terminate

### LearnTool
- **Module**: tools/learn_tool.py
- **Description**: Dynamically add new skills and tools
- **Operations**: add_skill, add_tool, list_skills, list_tools

### VoiceTool
- **Module**: tools/voice_tool.py
- **Description**: Text-to-speech and speech-to-text
- **Operations**: speak, listen, set_voice, set_rate

## Dynamic Tools
<!-- Auto-registered when agent learns new tools -->
