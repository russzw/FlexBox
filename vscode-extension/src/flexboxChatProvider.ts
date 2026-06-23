import * as vscode from 'vscode';

export class FlexBoxChatProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'flexbox.chat';
    
    private _view?: vscode.WebviewView;
    private _messages: Array<{role: string, content: string}> = [];
    
    constructor(private readonly _extensionUri: vscode.Uri) {}
    
    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };
        
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
        
        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.type) {
                    case 'sendMessage':
                        await this._handleMessage(message.text);
                        break;
                    case 'clear':
                        this._messages = [];
                        this._updateWebview();
                        break;
                }
            },
            undefined,
            []
        );
    }
    
    public show() {
        if (this._view) {
            this._view.show(true);
        }
    }
    
    private async _handleMessage(text: string) {
        // Add user message
        this._messages.push({ role: 'user', content: text });
        this._updateWebview();
        
        // Get active editor context
        const editor = vscode.window.activeTextEditor;
        let context = '';
        
        if (editor) {
            const selection = editor.document.getText(editor.selection);
            if (selection) {
                context = `\n\nSelected code:\n\`\`\`\n${selection}\n\`\`\``;
            }
            
            context += `\n\nFile: ${editor.document.fileName}`;
            context += `\nLanguage: ${editor.document.languageId}`;
        }
        
        // Simulate AI response (replace with actual Flex Box backend call)
        const response = await this._generateResponse(text + context);
        
        this._messages.push({ role: 'assistant', content: response });
        this._updateWebview();
    }
    
    private async _generateResponse(prompt: string): Promise<string> {
        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Simple response based on keywords
        const lowerPrompt = prompt.toLowerCase();
        
        if (lowerPrompt.includes('component') || lowerPrompt.includes('react')) {
            return `Here's a React component based on your request:

\`\`\`tsx
import React from 'react';

interface Props {
  children?: React.ReactNode;
}

export const CustomComponent: React.FC<Props> = ({ children }) => {
  return (
    <div className="p-4 rounded-lg bg-white shadow-sm">
      {children || <p>Custom component content</p>}
    </div>
  );
};
\`\`\`

This component:
- Uses TypeScript for type safety
- Accepts children prop for flexibility
- Includes basic Tailwind styling
- Follows modern React patterns

Would you like me to modify anything?`;
        }
        
        if (lowerPrompt.includes('style') || lowerPrompt.includes('css') || lowerPrompt.includes('tailwind')) {
            return `Here are the Tailwind CSS classes for your request:

\`\`\`css
/* Modern card styling */
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-100 p-6;
  @apply hover:shadow-md transition-shadow duration-200;
}

/* Responsive grid */
.grid-container {
  @apply grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6;
}
\`\`\`

Key features:
- Responsive breakpoints included
- Smooth hover transitions
- Consistent spacing
- Modern shadow and border styling`;
        }
        
        if (lowerPrompt.includes('config') || lowerPrompt.includes('setup')) {
            return `Here's the configuration:

\`\`\`json
{
  "compilerOptions": {
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
\`\`\`

This configuration enables:
- Strict TypeScript checking
- Path aliases for cleaner imports
- Modern module resolution`;
        }
        
        return `I can help you with that! Here's what I understand from your request:

"${prompt}"

I can generate:
- **React components** - Functional components with hooks
- **CSS/Tailwind** - Styling and layout
- **Configuration** - Project setup files

Please provide more details or select code in the editor for contextual help.`;
    }
    
    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'updateMessages',
                messages: this._messages,
            });
        }
    }
    
    private _getHtmlForWebview(webview: vscode.Webview): string {
        const nonce = getNonce();
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <title>Flex Box Chat</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }
        
        .message {
            margin-bottom: 12px;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 90%;
        }
        
        .message.user {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            margin-left: auto;
        }
        
        .message.assistant {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-widget-border);
        }
        
        .message pre {
            background: var(--vscode-textBlockQuote-background);
            padding: 8px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 8px 0;
            font-family: var(--vscode-editor-font-family);
            font-size: 12px;
        }
        
        .message code {
            font-family: var(--vscode-editor-font-family);
            font-size: 12px;
        }
        
        .input-container {
            padding: 12px;
            border-top: 1px solid var(--vscode-widget-border);
        }
        
        .input-row {
            display: flex;
            gap: 8px;
        }
        
        input {
            flex: 1;
            padding: 8px 12px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            outline: none;
        }
        
        input:focus {
            border-color: var(--vscode-focusBorder);
        }
        
        button {
            padding: 8px 16px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        button:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .toolbar {
            display: flex;
            gap: 4px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--vscode-widget-border);
        }
        
        .toolbar button {
            padding: 4px 8px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <button onclick="clearChat()">Clear</button>
    </div>
    
    <div class="chat-container" id="chatContainer">
        <div class="message assistant">
            Welcome to Flex Box! I can help you generate React components, CSS styles, and configuration files.
            <br><br>
            <strong>Tips:</strong>
            <ul style="margin-left: 16px; margin-top: 4px;">
                <li>Select code in the editor for contextual help</li>
                <li>Use <code>Cmd+Shift+K</code> to open chat</li>
                <li>Describe what you want to create</li>
            </ul>
        </div>
    </div>
    
    <div class="input-container">
        <div class="input-row">
            <input type="text" id="messageInput" placeholder="Describe what to generate..." />
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;
            
            vscode.postMessage({ type: 'sendMessage', text });
            messageInput.value = '';
        }
        
        function clearChat() {
            vscode.postMessage({ type: 'clear' });
        }
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        function renderMarkdown(text) {
            // Simple markdown rendering
            return text
                .replace(/\`\`\`\\w*\\n([\\s\\S]*?)\`\`\`/g, '<pre><code>$1</code></pre>')
                .replace(/\`\`(.*?)\`\`/g, '<code>$1</code>')
                .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\n/g, '<br>');
        }
        
        window.addEventListener('message', (event) => {
            const { type, messages } = event.data;
            
            if (type === 'updateMessages') {
                chatContainer.innerHTML = '';
                
                messages.forEach((msg) => {
                    const div = document.createElement('div');
                    div.className = \`message \${msg.role}\`;
                    div.innerHTML = renderMarkdown(msg.content);
                    chatContainer.appendChild(div);
                });
                
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        });
    </script>
</body>
</html>`;
    }
    
    public dispose() {
        this._view?.dispose();
    }
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
