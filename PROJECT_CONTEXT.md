# Lovable Clone - Project Context & Architecture

## 📋 Project Overview

**Lovable Clone** is an AI-powered React application generator similar to Lovable.dev, v0, or Bolt.new. It uses LangGraph (multi-agent architecture) to automatically build React applications based on user prompts.

### Core Features
- **AI-Driven Development**: Users provide prompts describing their desired app
- **Multi-Agent Architecture**: LangGraph workflow with specialized agents for different tasks
- **Sandbox Execution**: E2B sandbox environment for safe code execution
- **Real-time Streaming**: WebSocket support for live progress updates
- **Project Persistence**: Context and file storage for maintaining project state

---

## 🏗️ Architecture Overview

### Tech Stack
- **Backend**: Python + FastAPI
- **AI/LLMs**: 
  - Primary: Google Gemini 2.5 Pro
  - Fallback: OpenAI GPT-5
  - LLM Provider: LangChain
- **Orchestration**: LangGraph (multi-agent workflow)
- **Code Execution**: E2B Code Interpreter (sandbox)
- **Frontend Communication**: WebSocket
- **React Stack**: React + React Router + Tailwind CSS

### Project Structure

```
backend/
├── main.py                    # FastAPI server with WebSocket endpoints
├── agent/
│   ├── agent.py             # LLM initialization (Gemini, OpenAI, HuggingFace)
│   ├── graph_builder.py      # LangGraph workflow construction
│   ├── graph_nodes.py        # Individual agent nodes
│   ├── graph_state.py        # TypedDict state schema for workflow
│   ├── service.py            # Service layer with sandbox & workflow management
│   ├── tools.py              # Tool definitions for agents (create_file, execute_command, etc.)
│   ├── prompts.py            # Prompts for planning, building, validation
│   └── __init__.py
├── utils/
│   └── store.py              # File & JSON persistence layer
├── projects/                 # Project storage directory
├── inject.py                 # File listing utility for sandbox
├── pyproject.toml            # Project dependencies
├── e2b.Dockerfile            # E2B container configuration
└── e2b.toml                  # E2B template config
```

---

## 🔄 LangGraph Workflow

### Multi-Agent Pipeline

```
┌─────────┐      ┌─────────┐      ┌──────────────┐      ┌──────────────────┐
│ Planner │ ───→ │ Builder │ ───→ │Code Validator│ ───→ │Application Checker│
└─────────┘      └─────────┘      └──────────────┘      └──────────────────┘
                      ↑                   │                      │
                      │                   └──────────────────────┘
                      │ (retry on errors) 
                      └────────────────────────────────────────────
```

### Agent Nodes Explained

#### 1. **Planner Node** (`graph_nodes.py`)
- **Role**: Analyzes user prompts and creates implementation plans
- **Inputs**: User prompt, existing project context
- **Outputs**: Detailed JSON plan with components, pages, dependencies, file structure
- **LLM**: Gemini Pro
- **Process**:
  - Checks for previous work on the project (context retrieval)
  - Loads conversation history if project exists
  - Generates comprehensive implementation plan
  - Returns structured JSON

#### 2. **Builder Node** (`graph_nodes.py`)
- **Role**: Creates and modifies files based on the plan
- **Inputs**: Implementation plan, current errors (if retrying)
- **Outputs**: List of created/modified files
- **LLM**: Gemini Pro (via ReAct agent)
- **Tools Available**:
  - `create_file(path, content)` - Create/overwrite files
  - `execute_command(cmd)` - Run npm install, mkdir, etc.
  - `read_file(path)` - Read existing files
  - `write_multiple_files(json)` - Create multiple files efficiently
  - `get_context()` - Retrieve saved project context
  - `save_context()` - Save project documentation
- **Process**:
  - Creates ReAct agent with available tools
  - If fixing errors, focuses on specific issues
  - If building fresh, reads existing files first, then creates new components/pages
  - Calls `save_context()` at the end to document what was built

#### 3. **Code Validator Node** (`graph_nodes.py`)
- **Role**: Reviews code, checks dependencies, fixes syntax errors
- **Inputs**: Built files
- **Outputs**: List of validation errors (or empty if all good)
- **LLM**: Gemini Pro (via ReAct agent)
- **Tools Available**: Same as Builder Node
- **Process**:
  - Runs `check_missing_packages()` tool to identify missing npm packages
  - Installs missing packages via `execute_command(npm install)`
  - Reads and reviews each .jsx/.js file
  - Fixes syntax/import errors immediately
  - Validates component exports/imports
  - No build testing (focus on code quality only)

#### 4. **Application Checker Node** (`graph_nodes.py`)
- **Role**: Verifies application structure and runtime readiness
- **Inputs**: Validated code
- **Outputs**: List of runtime errors (or empty if all good)
- **Process**:
  - Checks for essential files (App.jsx, main.jsx, package.json)
  - Verifies project structure is complete
  - Does NOT test the dev server (environment is pre-configured)
  - Sets `success = true` if no errors found

### Retry Logic

- **Max Retries**: 3 per error type, 10 total across all types
- **Retry Decision Functions**:
  - `should_retry_builder_for_validation()`: Returns "builder" or "application_checker"
  - `should_retry_builder_or_finish()`: Returns "builder" or "end"
- **Error Categories**:
  - `import_errors` - Module not found, import path issues
  - `validation_errors` - Syntax errors, escaping issues
  - `runtime_errors` - Missing files, critical issues

---

## 📊 State Schema (`GraphState`)

```python
project_id: str                      # Unique project identifier
user_prompt: str                     # Original user request
enhanced_prompt: str                 # LLM-enhanced prompt

# Workflow data
plan: Optional[Dict]                 # Planner's implementation plan
files_created: List[str]             # Files created by builder
files_modified: List[str]            # Files modified

# Error tracking
current_errors: Dict                 # Current error batch
import_errors: List[Dict]            # Import-related errors
validation_errors: List[Dict]        # Code validation errors
runtime_errors: List[Dict]           # Runtime errors

# Execution tracking
retry_count: Dict[str, int]         # Per-error-type retry count
max_retries: int                     # Maximum retries (3)

# Environment
sandbox: Optional[AsyncSandbox]      # E2B sandbox instance
socket: Optional[WebSocket]          # WebSocket for streaming

# Communication
messages: List[BaseMessage]          # Conversation history
current_node: str                    # Current executing node
execution_log: List[Dict]            # Detailed execution log

# Results
success: bool                        # Whether workflow succeeded
final_url: Optional[str]             # Live app URL
error_message: Optional[str]         # Error details
```

---

## 🛠️ Tools (`tools.py`)

### Core Tools Available to Agents

1. **`create_file(path, content)`**
   - Creates or overwrites a file with content
   - Handles escape sequence fixes (\n, \t, etc.)
   - Sends `file_created` event via WebSocket

2. **`write_multiple_files(json_str)`**
   - Creates multiple files at once (batch operation)
   - More efficient than creating files one by one
   - Prevents agent from stopping prematurely

3. **`read_file(path)`**
   - Reads file content from sandbox
   - Used to check existing code before modification
   - Returns file content as string

4. **`execute_command(cmd)`**
   - Runs shell commands (npm install, mkdir, etc.)
   - Executed in `/home/user/react-app` directory
   - Returns stdout, stderr, exit_code
   - Sends `command_started`, `command_output`, `command_executed` events

5. **`delete_file(path)`**
   - Removes files from sandbox
   - Used for cleanup operations

6. **`list_directory(path)`**
   - Lists directory structure using `tree` command
   - Excludes node_modules and hidden files
   - Helps agents understand project structure

7. **`get_context()`**
   - Retrieves saved project context from disk
   - Returns semantic, procedural, episodic memory
   - Includes conversation history and files created

8. **`save_context(semantic, procedural, episodic)`**
   - Saves project documentation for future sessions
   - Updates conversation history
   - Persists project metadata

9. **`check_missing_packages()`**
   - Scans all src files for import statements
   - Checks against installed packages in package.json
   - Reports missing packages and provides install commands

10. **`test_build()`**
    - Runs `npm run build` to test compilation
    - Cleans Vite cache before building
    - Returns build success/failure with output

---

## 🌐 API Endpoints (`main.py`)

### 1. `POST /chat/{id}`
- **Purpose**: Initiate project creation
- **Payload**: `{"prompt": "Create a todo app"}`
- **Response**: `{"status": "success", "message": "..."}`
- **Process**:
  - Creates async task for agent workflow
  - Returns immediately (non-blocking)
  - Client connects via WebSocket to receive updates

### 2. `WebSocket /ws/{id}`
- **Purpose**: Stream real-time progress updates
- **Messages Sent**:
  - `{"e": "started", ...}` - Workflow started
  - `{"e": "planner_started", ...}` - Planner running
  - `{"e": "planner_complete", "plan": {...}}` - Plan ready
  - `{"e": "builder_started", ...}` - Builder running
  - `{"e": "file_created", ...}` - File created
  - `{"e": "command_executed", ...}` - Command finished
  - `{"e": "workflow_completed", "url": "..."}` - Success
  - `{"e": "workflow_error", "message": "..."}` - Error

### 3. `GET /projects/{id}/files`
- **Purpose**: Retrieve all project files
- **Response**: 
  ```json
  {
    "project_id": "...",
    "files": ["src/App.jsx", ...],
    "sandbox_id": "...",
    "sandbox_active": true
  }
  ```

---

## 💾 File Persistence (`utils/store.py`)

### Storage System
- **Location**: `backend/projects/{project_id}/`
- **Purpose**: Persist files and context across sessions

### Key Functions
- `save_json_store(id, filename, data)` - Save JSON data
- `load_json_store(id, filename)` - Load JSON data
- `save_context()` - Save project metadata
- `load_context()` - Load previous work

### Context File Structure
```json
{
  "semantic": "What the project is about",
  "procedural": "How it works (tech stack)",
  "episodic": "What has been built",
  "files_created": ["src/App.jsx", ...],
  "conversation_history": [
    {"timestamp": ..., "user_prompt": "...", "success": true}
  ],
  "last_updated": "..."
}
```

---

## 🐛 Recent Fix: Regex Escaping Issue

### Problem
- Files like `src/App.jsx` failing to create with error: `"bad escape (end of pattern) at position 0"`
- Root cause: Using `re.sub(r'\\n', '\n', content)` was causing regex interpretation issues

### Solution (Applied)
- Replaced regex-based string replacement with simple `.replace()` methods
- Changed from: `re.sub(r'\\n', '\n', content)`
- Changed to: `content.replace('\\n', '\n')`
- This eliminates regex parsing issues entirely

### Files Modified
- `backend/agent/tools.py` - `create_file()` function (lines ~30-50)

---

## 📝 Prompts & Instructions

### INITPROMPT (`prompts.py`)
- Long comprehensive prompt given to builder agents
- Contains 20+ critical sections with dos and don'ts
- Emphasizes:
  - Reading files FIRST before modifying
  - Not reinstalling already-installed packages
  - Completing the ENTIRE application (no early stopping)
  - Using `write_multiple_files()` for efficiency
  - Proper import/export syntax validation

### ENHANCED_PROMPT
- Used to validate and enhance user requests
- Transforms user input into technical specification
- Includes security validation

### Node-Specific Prompts
- `PLANNER_PROMPT` - For planning agents
- `BUILDER_PROMPT` - For building agents
- `IMPORT_CHECKER_PROMPT` - For import validation (currently unused)
- `APP_CHECKER_PROMPT` - For app checking (currently unused)

---

## 🔐 Security & Validation

### Request Validation
- `validate_request_security()` in `prompts.py`
- Checks for:
  - Malicious intent
  - Inappropriate content
  - Non-development-related requests
- Uses Gemini to analyze safety
- Blocks unsafe requests

---

## 🚀 Service Layer (`service.py`)

### Class: `Service`

#### Key Methods

**`get_e2b_sandbox(id)`**
- Gets or creates E2B sandbox for project
- Implements timeout management (3600 seconds)
- Restores files from disk on recreation
- Returns AsyncSandbox instance

**`run_agent_stream(prompt, id, socket)`**
- Main entry point for workflow
- Initializes GraphState with all parameters
- Runs LangGraph workflow
- Snapshots files to disk after completion
- Saves conversation history
- Returns final URL or error

**`snapshot_project_files(id)`**
- Saves all source files from sandbox to disk
- Stores files in `backend/projects/{id}/`
- Creates metadata.json with file list
- Enables project restoration on sandbox restart

---

## 🔄 Workflow Execution Flow

```
User sends prompt via POST /chat/{id}
         ↓
WebSocket connects at /ws/{id}
         ↓
get_e2b_sandbox() - Create/restore sandbox
         ↓
Initialize GraphState with user prompt
         ↓
LangGraph Workflow Starts
    ├─ Planner Node
    │   ├─ Load existing context
    │   ├─ Generate implementation plan
    │   └─ Return plan
    │
    ├─ Builder Node
    │   ├─ Create ReAct agent with tools
    │   ├─ Read existing files
    │   ├─ Create components/pages
    │   ├─ Update App.jsx
    │   └─ Return files created
    │
    ├─ Code Validator Node
    │   ├─ Run check_missing_packages()
    │   ├─ Install missing packages
    │   ├─ Review all files
    │   ├─ Fix syntax errors
    │   └─ Return validation errors (if any)
    │
    └─ Application Checker Node
        ├─ Check file structure
        ├─ Verify essential files exist
        └─ Return runtime errors (if any)

If errors found → Retry with Builder Node (max 3 retries)
If no errors → Success
         ↓
snapshot_project_files() - Save to disk
         ↓
save_conversation_history() - Store in context
         ↓
Send final URL via WebSocket
```

---

## ⚙️ Configuration Files

### `pyproject.toml`
```
Python 3.12+
Dependencies: FastAPI, E2B, LangChain, LangGraph, etc.
```

### `e2b.toml`
```
Template ID: 63i6x6z8nd0uzadokgzg
Start command: cd react-app && npm run dev
Dockerfile: e2b.Dockerfile
```

### `.env`
```
GOOGLE_API_KEY=...
HUGGINGFACEHUB_API_TOKEN=...
OPENAI_API_KEY=...
```

---

## 🎯 Key Design Decisions

1. **LangGraph Over Simple Agent**: 
   - Structured workflow with multiple specialized agents
   - Built-in error handling and retry logic
   - Better control over process flow

2. **E2B Sandbox**:
   - Isolated execution environment
   - Pre-configured with React dev setup
   - Automatic file sync and persistence

3. **WebSocket Streaming**:
   - Real-time progress updates
   - User sees what agent is doing step-by-step
   - Better UX than polling

4. **Tool-Based Agent Architecture**:
   - Agents have access to file operations
   - Can read existing code before modifying
   - Can install packages and run commands
   - Prevents hallucinations with real feedback

5. **Context & Memory**:
   - Saves project documentation
   - Maintains conversation history
   - Enables multi-turn project development
   - Supports "continue building on previous project" requests

---

## 🐛 Current Issues & Known Limitations

1. **Regex Escaping (FIXED)**: Was causing file creation failures
2. **Long Processing Times**: Agents can take 10+ minutes for complex apps
3. **Retry Limits**: Safety measure prevents infinite loops, but might stop too early
4. **Error Messages**: Could be more granular for debugging
5. **LLM Consistency**: Different LLM runs may produce different code quality

---

## 📚 How to Use This Project

### Starting a New Build
```bash
curl -X POST http://localhost:8000/chat/my-project-1 \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a todo list app with dark mode"}'

# Connect to WebSocket
ws://localhost:8000/ws/my-project-1
```

### Retrieving Project Files
```bash
curl http://localhost:8000/projects/my-project-1/files
```

### Continuing Work on Existing Project
```bash
# Agents automatically load previous context
curl -X POST http://localhost:8000/chat/my-project-1 \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add a feature to export tasks as PDF"}'
```

---

## 🎓 Understanding Code Quality

### Why Code Validator is Important
- Checks for missing npm packages before builder finishes
- Fixes common mistakes (wrong imports, escape sequences)
- Ensures app can actually run before declaring success

### Why Application Checker Exists
- Final verification that project structure is correct
- Checks for essential files
- Provides early warning if something is fundamentally broken

### Why Retry Logic Exists
- Gives builder chances to fix mistakes
- Max 3 retries per error type prevents infinite loops
- 10 total retries across all types prevents runaway processes

---

## 📞 Support & Debugging

### Check Service Status
```python
# service.py
print(f"Active sandboxes: {len(service.sandboxes)}")
print(f"Active runs: {len(active_runs)}")
```

### View Execution Log
```python
# final_state["execution_log"] contains detailed execution history
for entry in final_state["execution_log"]:
    print(f"{entry['node']}: {entry['status']}")
```

### Retrieve Saved Context
```python
# Manual context retrieval
from utils.store import load_json_store
context = load_json_store("project-id", "context.json")
```

---

## 🔮 Future Improvements

1. Add support for other frameworks (Vue, Next.js, Svelte)
2. Implement caching for frequently used components
3. Add version control integration (Git)
4. Better error recovery with more granular retry logic
5. Support for more LLM providers
6. Analytics on build success rates and timing
7. Component library and reusable templates

---

**Last Updated**: October 27, 2025
**Status**: Functional - Recent fix for regex escaping applied
