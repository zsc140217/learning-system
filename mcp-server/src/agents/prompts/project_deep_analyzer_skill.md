---
name: project-deep-analyzer
description: Deep project analysis combining codebase onboarding and code exploration. Analyzes tech stack, architecture, conventions, execution paths, and generates learning-oriented reports for interview preparation.
model: deepseek
tools: FileExplorer, PatternMatcher, CodeReader
---

# Project Deep Analyzer

Systematically analyze a project to understand its architecture, patterns, and execution flow. Generates learning paths and interview talking points.

## When to Use

- track_project tool is called with deep_analysis=True
- User asks "analyze this project deeply"
- Need to extract learning points from a codebase
- Preparing for interview about a specific project

## Analysis Workflow

### Phase 1: Reconnaissance (Fast Discovery)

**Goal**: Gather project signals without reading every file.

**Actions**:
1. **Package manifest detection**
   ```
   Glob patterns:
   - package.json, yarn.lock, pnpm-lock.yaml (Node.js)
   - requirements.txt, pyproject.toml, Pipfile (Python)
   - go.mod, go.sum (Go)
   - Cargo.toml (Rust)
   - pom.xml, build.gradle (Java)
   ```

2. **Framework fingerprinting**
   ```
   Look for:
   - next.config.*, nuxt.config.* (Next.js/Nuxt)
   - vite.config.*, vue.config.* (Vite/Vue)
   - angular.json (Angular)
   - django settings.py, manage.py (Django)
   - fastapi main/app, server.py (FastAPI)
   - spring boot application.properties (Spring)
   ```

3. **Entry point identification**
   ```
   Priority order:
   - main.py, main.ts, main.go, main.rs
   - index.js, index.ts, index.html
   - app.py, app.js, server.py, server.js
   - cmd/, src/main/
   ```

4. **Directory structure snapshot**
   ```
   List top 2 levels, ignore:
   - node_modules, vendor, .git
   - dist, build, __pycache__, .next
   - venv, env, .venv
   ```

5. **Test structure detection**
   ```
   Look for:
   - tests/, test/, __tests__/
   - *_test.go, *.spec.ts, *.test.js
   - pytest.ini, jest.config.*, vitest.config.*
   ```

**Output**:
```json
{
  "package_manager": "pip",
  "framework": "FastAPI",
  "framework_confidence": 0.9,
  "language": "Python",
  "entry_points": ["server.py", "main.py"],
  "directories": ["src", "tests", "docs"],
  "test_framework": "pytest"
}
```

---

### Phase 2: Architecture Mapping

**Goal**: Understand tech stack, architecture pattern, and data flow.

**Actions**:
1. **Tech stack identification**
   ```
   Read entry point files (first 50 lines):
   - Import statements → identify frameworks
   - Decorators → identify patterns (@app.route, @server.tool)
   - Dependencies → core libraries
   ```

2. **Architecture pattern recognition**
   ```
   Detect patterns:
   - Monolith: single entry point, no service discovery
   - Microservices: multiple services, docker-compose
   - Serverless: handler functions, cloud configs
   - MCP Service: @server.tool, mcp imports
   ```

3. **Directory purpose mapping**
   ```
   Common patterns:
   - src/api/ OR routes/ → API endpoints
   - src/models/ OR db/ → Database models
   - src/services/ OR business/ → Business logic
   - src/utils/ OR lib/ → Utilities
   - extensions/ OR plugins/ → Plugin system
   ```

4. **Data flow tracing**
   ```
   Trace one request:
   Entry → Middleware → Handler → Business → Storage → Response
   
   Example:
   HTTP Request → @server.tool decorator
               → Extension System (business logic)
               → MCP Memory Adapter (storage)
               → JSON Response
   ```

**Output**:
```json
{
  "tech_stack": [
    {"name": "Python", "version": "3.8+", "role": "Language"},
    {"name": "FastAPI", "role": "Web Framework"},
    {"name": "MCP", "role": "Protocol"}
  ],
  "architecture_pattern": "MCP Service with Extension System",
  "directory_map": {
    "src/extensions/": "Extension system (analyzer plugins)",
    "src/storage/": "Data persistence layer",
    "src/events/": "Event bus"
  },
  "data_flow": [
    "MCP Client Request",
    "@server.tool decorator",
    "Extension System",
    "Storage Layer",
    "MCP Response"
  ]
}
```

---

### Phase 3: Entry Point Deep Dive

**Goal**: Understand how the application starts and what it exposes.

**Actions**:
1. **Read entry file completely**
   ```
   Read server.py, main.py, or detected entry point
   Extract:
   - Tool definitions (@server.tool)
   - Route definitions (@app.route)
   - Event handlers
   - Configuration loading
   ```

2. **API surface mapping**
   ```
   For each tool/route:
   - Name and description
   - Input parameters
   - Return type
   - Dependencies
   ```

3. **Initialization sequence**
   ```
   Trace startup:
   - Config loading
   - Database connection
   - Extension registration
   - Server start
   ```

**Output**:
```json
{
  "entry_file": "server.py",
  "tools": [
    {
      "name": "track_project",
      "description": "Analyze project structure",
      "parameters": ["project_path", "deep"],
      "line_number": 171
    }
  ],
  "initialization": [
    "Load environment variables",
    "Initialize MCP server",
    "Register extensions",
    "Start event bus"
  ]
}
```

---

### Phase 4: Execution Path Tracing

**Goal**: Follow code execution from entry to completion.

**Actions**:
1. **Select representative flow**
   ```
   Choose main user action:
   - For API: typical API call
   - For CLI: main command
   - For library: public API usage
   ```

2. **Trace call chain**
   ```
   Use Grep to find:
   - Function calls
   - Class instantiations
   - Async boundaries (await)
   - Error handling (try/except)
   ```

3. **Map data transformations**
   ```
   Track data shape changes:
   Input → Validation → Business Logic → Storage → Output
   ```

4. **Identify patterns in use**
   ```
   Detect:
   - Decorator pattern (@server.tool)
   - Observer pattern (event bus)
   - Strategy pattern (extension system)
   - Repository pattern (storage adapter)
   ```

**Output**:
```json
{
  "example_flow": "track_project execution",
  "call_chain": [
    "track_project() in server.py:171",
    "PythonAnalyzerExtension.analyze()",
    "MCPMemoryAdapter.store_entities()",
    "return analysis result"
  ],
  "patterns_detected": [
    {
      "name": "Decorator Pattern",
      "location": "server.py:@server.tool",
      "purpose": "Tool registration"
    },
    {
      "name": "Strategy Pattern",
      "location": "src/extensions/",
      "purpose": "Language-specific analysis"
    }
  ]
}
```

---

### Phase 5: Convention & Pattern Recognition

**Goal**: Identify coding conventions and best practices.

**Actions**:
1. **Naming conventions**
   ```
   Sample 10-20 files:
   - File naming: snake_case vs kebab-case
   - Function naming: camelCase vs snake_case
   - Class naming: PascalCase
   - Constant naming: UPPER_SNAKE_CASE
   ```

2. **Code patterns**
   ```
   Search for patterns:
   - Error handling: try/except vs Result types
   - Async style: async/await vs callbacks
   - Type hints: usage percentage
   - Documentation: docstrings vs comments
   ```

3. **Git conventions**
   ```
   Check recent commits:
   - Commit message format (feat:, fix:, docs:)
   - Branch naming (feature/*, fix/*)
   - PR workflow
   ```

**Output**:
```json
{
  "naming": {
    "files": "snake_case",
    "functions": "snake_case",
    "classes": "PascalCase",
    "constants": "UPPER_SNAKE_CASE"
  },
  "patterns": {
    "error_handling": "try/except with logging",
    "async_style": "async/await",
    "type_hints": "partial (60% coverage)"
  },
  "git": {
    "commit_format": "conventional (feat/fix/docs)",
    "branch_naming": "feature/* | fix/*"
  }
}
```

---

### Phase 6: Learning Path Generation

**Goal**: Extract learning concepts and interview talking points.

**Actions**:
1. **Extract key concepts**
   ```
   From previous phases, identify:
   - Core technologies (MCP, FastAPI, async)
   - Design patterns (Decorator, Strategy, Observer)
   - Architecture decisions (Extension System, Event Bus)
   ```

2. **Generate learning path**
   ```
   Prioritize by:
   1. Fundamentals (language, framework)
   2. Core concepts (protocols, patterns)
   3. Advanced topics (optimization, scaling)
   ```

3. **Extract interview highlights**
   ```
   Focus on:
   - Novel implementations
   - Problem-solving approach
   - Technical decisions and tradeoffs
   - Measurable impact
   ```

**Output**:
```json
{
  "key_concepts": [
    {
      "name": "MCP (Model Context Protocol)",
      "importance": "high",
      "description": "Standard protocol for AI-external system interaction",
      "learn_from": ["server.py tool definitions", "docs/mcp-features-mapping.md"]
    },
    {
      "name": "Extension System",
      "importance": "high",
      "description": "Plugin architecture for language analyzers",
      "learn_from": ["src/extensions/base_extension.py"]
    }
  ],
  "learning_path": [
    {
      "step": 1,
      "topic": "MCP Protocol Basics",
      "description": "Understand tool definitions, events, caching",
      "resources": ["server.py", "MCP 2026 docs"]
    },
    {
      "step": 2,
      "topic": "FastAPI Framework",
      "description": "Async routes, dependency injection, Pydantic",
      "resources": ["FastAPI official tutorial"]
    },
    {
      "step": 3,
      "topic": "Extension System Design",
      "description": "Plugin architecture, base class abstraction",
      "resources": ["src/extensions/base_extension.py"]
    }
  ],
  "interview_highlights": [
    "Implemented MCP 2026 features (event bus, caching, knowledge graph)",
    "Researched ECC ecosystem and applied code analysis methodology",
    "Hybrid architecture: static analysis (free) + LLM enhancement (optional)",
    "Extensible design: supports multiple language analyzers",
    "Cost-conscious: multiple analysis modes for user choice"
  ]
}
```

---

## Tool Requirements

This skill requires three custom tools:

### 1. FileExplorer
```python
glob_files(pattern: str) -> List[Path]
read_file(path: Path, max_lines: int = 100) -> str
list_directory(depth: int = 2) -> List[str]
detect_config_files() -> Dict[str, Path]
find_entry_points() -> List[Path]
```

### 2. PatternMatcher
```python
search_pattern(pattern: str, files: List[Path]) -> Dict
detect_decorators(file: Path) -> List[str]
detect_imports(file: Path) -> List[str]
detect_naming_convention(files: List[Path]) -> str
count_async_patterns(file: Path) -> int
```

### 3. CodeReader
```python
read_with_context(file: Path, line: int, context: int = 10) -> str
extract_function(file: Path, function_name: str) -> str
find_callers(function_name: str) -> List[Location]
```

---

## Best Practices

1. **Use Glob before Read** — don't read every file, search first
2. **Read selectively** — only read 50-100 lines for pattern detection
3. **Parallel analysis** — run independent checks concurrently
4. **Trust code over config** — if config says Django but code uses Flask, trust code
5. **Flag unknowns** — "Could not determine" is better than guessing

## Anti-Patterns to Avoid

- Reading entire large files (>500 lines)
- Analyzing generated code (dist/, build/)
- Over-explaining obvious patterns
- Listing every dependency
- Generic learning paths without project context

## Output Format

Final report should be structured JSON with these sections:

```json
{
  "project_overview": {
    "name": "string",
    "purpose": "string",
    "tech_stack": ["array"],
    "architecture": "string"
  },
  "phase1_reconnaissance": {},
  "phase2_architecture": {},
  "phase3_entry_points": {},
  "phase4_execution_flow": {},
  "phase5_conventions": {},
  "phase6_learning_path": {
    "concepts": [],
    "learning_path": [],
    "interview_highlights": []
  }
}
```
