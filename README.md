# Flex Box

**Local-first AI coding assistant with LoRA adapter swapping**

Flex Box is a specialized, local-first multi-agent development environment powered by LoRA-swapping orchestration. Instead of relying on monolithic cloud LLMs, Flex Box runs a single optimized base model locally and dynamically hot-swaps lightweight LoRA adapters for different coding tasks.

---

## Features

- **LoRA Adapter Swapping** - Hot-swap specialized adapters (FlexReact, FlexCSS, FlexConfig) without reloading the base model
- **Task Router** - Automatically detects the right adapter based on your prompt
- **Project Memory** - Scans your workspace to understand framework, styling, and project structure
- **VS Code Extension** - Inline chat, diff viewer, and keyboard shortcuts
- **Web UI** - Browser-based chat interface
- **Privacy-First** - Everything runs locally, no data leaves your machine
- **Enterprise Ready** - Docker/Kubernetes deployment, PII scrubbing, corporate adapters

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train Adapters (Optional)

If you have trained adapters from Google Colab, place them in the `adapters/` folder:

```
adapters/
├── flexreact/
│   ├── adapter_config.json
│   └── adapter_model.safetensors
├── flexcss/
│   ├── adapter_config.json
│   └── adapter_model.safetensors
└── flexconfig/
    ├── adapter_config.json
    └── adapter_model.safetensors
```

Or use the training scripts with Google Colab (see `COLAB_TRAINING.md`).

### 3. Start the Server

```bash
python -m flexbox.server
```

The server starts on `http://127.0.0.1:8181`.

### 4. Use Flex Box

**CLI:**
```bash
python -m flexbox.cli route "Create a React button"
python -m flexbox.cli generate "Create a React button" --adapter flexreact
python -m flexbox.cli adapters
```

**Web UI:**
Open `web-ui/index.html` in your browser.

**VS Code Extension:**
Install the extension from `vscode-extension/` (see below).

---

## Architecture

```
[User Prompt]
      │
      ▼
[Task Router] ──► Detects adapter (flexreact/flexcss/flexconfig)
      │
      ▼
[Project Memory] ──► Injects context (framework, styling, files)
      │
      ▼
[Inference Engine] ──► Swaps LoRA adapter, generates code
      │
      ▼
[Response] ──► Code with adapter badge
```

---

## Components

| Component | Description |
|-----------|-------------|
| `src/flexbox/core/` | Task Router, Adapter Manager, Inference Engine, Project Memory |
| `src/flexbox/orchestrator.py` | Main FlexBox orchestrator |
| `src/flexbox/server.py` | HTTP API server |
| `src/flexbox/cli.py` | Command-line interface |
| `src/flexbox/datasets/` | Dataset generators for training |
| `src/flexbox/fine_tuning/` | LoRA training configuration |
| `src/flexbox/enterprise/` | Headless runtime, Gateway, Security |
| `vscode-extension/` | VS Code extension |
| `web-ui/` | Browser-based chat interface |
| `docker/` | Docker configuration |
| `k8s/` | Kubernetes manifests |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/generate` | POST | Generate code from prompt |
| `/api/v1/route` | POST | Route prompt to adapter |
| `/api/v1/adapters` | GET | List available adapters |
| `/api/v1/context` | GET | Get project context |

**Example Request:**
```bash
curl -X POST http://localhost:8181/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a React button", "adapter": "flexreact"}'
```

---

## VS Code Extension

### Install

```bash
cd vscode-extension
npm install
npm run compile
npm run package
```

Then install the `.vsix` file in VS Code.

### Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| `Flex Box: Open Chat` | `Cmd+Shift+K` | Open chat panel |
| `Flex Box: Generate Code` | `Cmd+Shift+G` | Generate from selection |
| `Flex Box: Open Diff Panel` | - | View side-by-side diff |
| `Flex Box: Clear Context` | - | Clear project memory |
| `Flex Box: Refresh Memory` | - | Rescan project |

### Features

- **Chat Panel** - Sidebar chat with AI assistant
- **Diff Viewer** - Side-by-side code comparison with Apply/Reject
- **Project Context** - Shows detected framework, styling, file stats
- **Adapter Selection** - Auto-detects or manually select adapter
- **Code Insertion** - Insert generated code directly into editor

---

## Training Adapters

See `COLAB_TRAINING.md` for detailed instructions.

### Quick Training (Google Colab)

1. Open Google Colab
2. Clone the repository
3. Run the training cells
4. Download trained adapters
5. Place in `adapters/` folder

### Training Locally (requires GPU)

```bash
python src/flexbox/training/train_flexreact.py \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset datasets/react_train.jsonl \
    --output adapters/flexreact \
    --epochs 3 \
    --rank 8
```

---

## Enterprise Features

### FlexCorp Gateway

Centralized inference server for enterprise deployment:

```bash
docker-compose up -d
```

### Security

- **PII Scrubbing** - Removes personal information from prompts
- **Credential Detection** - Blocks API keys, tokens, passwords
- **Privacy Firewall** - Prevents sensitive data from leaving the network

### Corporate Adapters

Train custom adapters on your organization's codebase:

```python
from flexbox.enterprise.corporate.pipeline import CorporatePipeline

pipeline = CorporatePipeline(config)
pipeline.run()
```

---

## Configuration

### Environment Variables

```bash
FLEXBOX_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
FLEXBOX_HOST=127.0.0.1
FLEXBOX_PORT=8181
FLEXBOX_ADAPTERS_DIR=adapters
```

### VS Code Settings

```json
{
    "flexbox.model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "flexbox.adaptersPath": "adapters",
    "flexbox.autoApply": false,
    "flexbox.maxTokens": 512
}
```

---

## Requirements

- Python 3.10+
- PyTorch 2.0+
- 8GB+ RAM (16GB recommended)
- GPU optional (significantly faster)

---

## License

MIT

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## Support

- **Issues:** GitHub Issues
- **Docs:** See `docs/` folder
- **Training:** See `COLAB_TRAINING.md`
