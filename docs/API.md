# Flex Box API Documentation

## Base URL

```
http://127.0.0.1:8181
```

---

## Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "uptime": 123.45,
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "adapters": ["flexreact", "flexcss", "flexconfig"]
}
```

---

### Generate Code

```
POST /api/v1/generate
```

**Request Body:**
```json
{
    "prompt": "Create a React button component with useState",
    "adapter": "flexreact",
    "system_prompt": "Optional system context",
    "max_tokens": 512
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The code generation prompt |
| `adapter` | string | No | Adapter to use (auto-detected if not provided) |
| `system_prompt` | string | No | Custom system prompt |
| `max_tokens` | int | No | Maximum tokens to generate (default: 512) |

**Response:**
```json
{
    "text": "import React from 'react';\n\ninterface ButtonProps {\n  children: React.ReactNode;\n  onClick?: () => void;\n}\n\nexport const Button: React.FC<ButtonProps> = ({ children, onClick }) => {\n  return (\n    <button onClick={onClick} className=\"px-4 py-2 bg-blue-500 text-white rounded\">\n      {children}\n    </button>\n  );\n};",
    "adapter_used": "flexreact",
    "tokens_generated": 156,
    "latency_ms": 234.5
}
```

---

### Route Prompt

```
POST /api/v1/route
```

**Request Body:**
```json
{
    "prompt": "Create a React hero section with Tailwind CSS"
}
```

**Response:**
```json
{
    "primary_adapter": "flexreact",
    "subtasks": [
        {"adapter": "flexreact", "priority": 1},
        {"adapter": "flexcss", "priority": 1}
    ],
    "multi_adapter": true
}
```

---

### List Adapters

```
GET /api/v1/adapters
```

**Response:**
```json
{
    "adapters": {
        "flexreact": {"path": "adapters/flexreact"},
        "flexcss": {"path": "adapters/flexcss"},
        "flexconfig": {"path": "adapters/flexconfig"}
    }
}
```

---

### Get Project Context

```
GET /api/v1/context
```

**Response:**
```json
{
    "context": "Framework: Next.js | Styling: Tailwind CSS | Root: my-project"
}
```

---

## Python Client

```python
import requests

API_BASE = "http://127.0.0.1:8181"

# Generate code
response = requests.post(f"{API_BASE}/api/v1/generate", json={
    "prompt": "Create a React button",
    "adapter": "flexreact",
})
print(response.json()["text"])

# Route prompt
response = requests.post(f"{API_BASE}/api/v1/route", json={
    "prompt": "Add hover effects with Tailwind CSS",
})
print(response.json()["primary_adapter"])

# List adapters
response = requests.get(f"{API_BASE}/api/v1/adapters")
print(response.json()["adapters"])
```

---

## JavaScript Client

```javascript
const API_BASE = 'http://127.0.0.1:8181';

// Generate code
async function generate(prompt, adapter) {
    const res = await fetch(`${API_BASE}/api/v1/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, adapter }),
    });
    return await res.json();
}

// Route prompt
async function route(prompt) {
    const res = await fetch(`${API_BASE}/api/v1/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
    });
    return await res.json();
}

// List adapters
async function getAdapters() {
    const res = await fetch(`${API_BASE}/api/v1/adapters`);
    return await res.json();
}
```

---

## cURL Examples

**Generate React component:**
```bash
curl -X POST http://localhost:8181/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a React button with useState", "adapter": "flexreact"}'
```

**Generate CSS:**
```bash
curl -X POST http://localhost:8181/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add hover effects with Tailwind CSS", "adapter": "flexcss"}'
```

**Auto-detect adapter:**
```bash
curl -X POST http://localhost:8181/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a gradient background"}'
```

---

## Error Responses

```json
{
    "error": "Missing prompt"
}
```

```json
{
    "error": "Connection failed: Connection refused"
}
```

---

## Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (missing parameters) |
| 500 | Server error |
