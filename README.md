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

### 2. Start the Server

```bash
python -m flexbox.server
```

The server starts on `http://127.0.0.1:8181`. Open this URL in your browser to access the Web UI.

### 3. Use Flex Box

**Web UI:**
Navigate to `http://127.0.0.1:8181` in your browser.

**CLI:**
```bash
python -m flexbox.cli route "Create a React button"
python -m flexbox.cli generate "Create a React button" --adapter flexreact
python -m flexbox.cli adapters
```

**VS Code Extension:**
Install the extension from `vscode-extension/` (see below).

---

## Model Sizes & Hardware Requirements

Flex Box supports different model sizes depending on your available RAM:

| Model | RAM Required | Adapter Compatible | Quality |
|-------|-------------|-------------------|---------|
| `Qwen2.5-Coder-0.5B` | 4GB+ | Requires retraining | Basic |
| `Qwen2.5-Coder-1.5B` | 8GB+ | Requires retraining | Good |
| `Qwen2.5-Coder-7B` | 16GB+ | Yes (trained adapters) | Best |

### Important: Adapter Compatibility

**LoRA adapters are model-size specific.** Adapters trained on one model size **cannot** be used with a different size. The default adapters included were trained on the 7B model.

- **8GB RAM (like your system):** Server runs with 0.5B model. Adapters won't load (size mismatch), but the base model still generates code.
- **16GB+ RAM:** Full experience with 7B model and trained adapters.
- **Retrain for your model:** Use Google Colab to train adapters on 0.5B or 1.5B (see `COLAB_TRAINING.md`).

The server automatically:
1. Detects available RAM
2. Selects the appropriate model
3. Falls back to base model if adapters are incompatible

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
| `/` | GET | Web UI |
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

### Retraining for Low-RAM Systems

If you have 8GB RAM, train adapters on the 0.5B model in Colab:

```python
!python3 src/flexbox/training/train_flexreact.py \
    --model Qwen/Qwen2.5-Coder-0.5B-Instruct \
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

### Server Config (src/flexbox/server.py)

```python
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8181
    model_name: str = "Qwen/Qwen2.5-Coder-0.5B-Instruct"  # Change to 7B for full experience
    adapters_dir: str = "adapters"
    max_tokens: int = 512
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

### Minimum (0.5B model)
- Python 3.10+
- PyTorch 2.0+
- 4GB RAM
- No GPU required

### Recommended (7B model)
- Python 3.10+
- PyTorch 2.0+
- 16GB+ RAM
- GPU optional (significantly faster)

---

## Troubleshooting

### "CUDA out of memory" or PC crashes
- You don't have enough GPU VRAM
- Server falls back to CPU mode automatically
- Close other applications to free RAM

### "size mismatch" adapter errors
- Adapters trained on 7B can't load on 0.5B model
- Server falls back to base model (no adapter specialization)
- Retrain adapters on your model size (see Training section)

### Server not responding
- Check if port 8181 is in use: `netstat -ano | findstr 8181`
- Try a different port in `server.py`

### Model download slow
- First run downloads the model (~1-10GB depending on size)
- Subsequent runs use the cache

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
