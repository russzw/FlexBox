import * as vscode from 'vscode';
import { FlexBoxClient } from './flexboxClient';

export class FlexBoxChatProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'flexbox.chat';
    
    private _view?: vscode.WebviewView;
    private _messages: Array<{role: string, content: string, adapter?: string}> = [];
    private _client: FlexBoxClient;
    private _isGenerating: boolean = false;
    
    constructor(private readonly _extensionUri: vscode.Uri) {
        this._client = new FlexBoxClient();
    }
    
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
                    case 'insertCode':
                        await this._insertCode(message.code);
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
        if (this._isGenerating) {
            return;
        }
        
        this._isGenerating = true;
        this._updateWebview();
        
        this._messages.push({ role: 'user', content: text });
        this._updateWebview();
        
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
        
        try {
            // Check if server is running
            const isRunning = await this._client.isServerRunning();
            
            let response: string;
            let adapterUsed: string;
            
            if (isRunning) {
                // Use real backend
                const result = await this._client.generate(text + context);
                response = result.text;
                adapterUsed = result.adapter_used;
            } else {
                // Fallback to local generation
                const fallback = this._localGenerate(text + context);
                response = fallback.text;
                adapterUsed = fallback.adapter;
            }
            
            this._messages.push({ role: 'assistant', content: response, adapter: adapterUsed });
            this._updateWebview();
            
        } catch (error: any) {
            this._messages.push({ 
                role: 'assistant', 
                content: `Error: ${error.message}\n\nMake sure the Flex Box server is running:\n\`\`\`\npython -m flexbox.server\n\`\`\`` 
            });
            this._updateWebview();
        } finally {
            this._isGenerating = false;
            this._updateWebview();
        }
    }
    
    private _localGenerate(prompt: string): { text: string, adapter: string } {
        const lowerPrompt = prompt.toLowerCase();
        
        if (lowerPrompt.includes('component') || lowerPrompt.includes('react')) {
            return {
                adapter: 'flexreact',
                text: `Here's a React component:

\`\`\`tsx
import React from 'react';

interface Props {
  children?: React.ReactNode;
}

export const CustomComponent: React.FC<Props> = ({ children }) => {
  return (
    <div className="p-4 rounded-lg bg-white shadow-sm">
      {children || <p>Component content</p>}
    </div>
  );
};
\`\`\`

*Start the Flex Box server for AI-powered generation:*
\`\`\`
python -m flexbox.server
\`\`\``,
            };
        }
        
        if (lowerPrompt.includes('style') || lowerPrompt.includes('css') || lowerPrompt.includes('tailwind')) {
            return {
                adapter: 'flexcss',
                text: `Here's the CSS:

\`\`\`css
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-100 p-6;
  @apply hover:shadow-md transition-shadow duration-200;
}
\`\`\`

*Start the Flex Box server for AI-powered generation:*
\`\`\`
python -m flexbox.server
\`\`\``,
            };
        }
        
        return {
            adapter: 'flexconfig',
            text: `I can help you with that! Here's what I understand:

"${prompt}"

**Available adapters:**
- **flexreact** - React/JSX components
- **flexcss** - Tailwind CSS styles
- **flexconfig** - Configuration files

*Start the Flex Box server for AI-powered generation:*
\`\`\`
python -m flexbox.server
\`\`\``,
        };
    }
    
    private async _insertCode(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }
        
        await editor.edit(editBuilder => {
            if (editor.selection.isEmpty) {
                editBuilder.insert(editor.selection.active, code);
            } else {
                editBuilder.replace(editor.selection, code);
            }
        });
    }
    
    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'updateMessages',
                messages: this._messages,
                isGenerating: this._isGenerating,
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
            word-wrap: break-word;
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
        
        .message .adapter-badge {
            display: inline-block;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            margin-top: 4px;
        }
        
        .message .copy-btn {
            display: inline-block;
            font-size: 11px;
            padding: 4px 8px;
            margin-top: 4px;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .message .copy-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        
        .generating {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            color: var(--vscode-descriptionForeground);
            font-style: italic;
        }
        
        .generating .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid var(--vscode-widget-border);
            border-top-color: var(--vscode-progressBar-background);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
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
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
                <li>Start the server: <code>python -m flexbox.server</code></li>
            </ul>
        </div>
    </div>
    
    <div class="input-container">
        <div class="input-row">
            <input type="text" id="messageInput" placeholder="Describe what to generate..." />
            <button id="sendBtn" onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;
            
            vscode.postMessage({ type: 'sendMessage', text });
            messageInput.value = '';
        }
        
        function clearChat() {
            vscode.postMessage({ type: 'clear' });
        }
        
        function insertCode(code) {
            vscode.postMessage({ type: 'insertCode', code });
        }
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !sendBtn.disabled) sendMessage();
        });
        
        function renderMarkdown(text) {
            // Extract code blocks
            let html = text.replace(/\`\`\`(\\w*)\\n([\\s\\S]*?)\`\`\`/g, (match, lang, code) => {
                const escapedCode = code.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return '<pre><code>' + escapedCode + '</code></pre>';
            });
            
            // Inline code
            html = html.replace(/\`\`(.*?)\`\`/g, '<code>$1</code>');
            
            // Bold
            html = html.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
            
            // Lists
            html = html.replace(/^- (.*)/gm, '<li>$1</li>');
            html = html.replace(/(<li>.*<\\/li>)/s, '<ul>$1</ul>');
            
            // Line breaks
            html = html.replace(/\\n/g, '<br>');
            
            return html;
        }
        
        window.addEventListener('message', (event) => {
            const { type, messages, isGenerating } = event.data;
            
            if (type === 'updateMessages') {
                chatContainer.innerHTML = '';
                
                messages.forEach((msg) => {
                    const div = document.createElement('div');
                    div.className = 'message ' + msg.role;
                    
                    let content = renderMarkdown(msg.content);
                    
                    if (msg.role === 'assistant' && msg.adapter) {
                        content += '<div class="adapter-badge">Adapter: ' + msg.adapter + '</div>';
                    }
                    
                    // Add insert button for code blocks
                    if (msg.role === 'assistant' && msg.content.includes('\`\`\`')) {
                        const codeMatch = msg.content.match(/\`\`\`\\w*\\n([\\s\\S]*?)\`\`\`/);
                        if (codeMatch) {
                            const code = codeMatch[1].trim();
                            content += '<button class="copy-btn" onclick="insertCode(\`' + 
                                code.replace(/`/g, '\\`').replace(/\\/g, '\\\\') + 
                                '\`)">Insert Code</button>';
                        }
                    }
                    
                    div.innerHTML = content;
                    chatContainer.appendChild(div);
                });
                
                if (isGenerating) {
                    const generatingDiv = document.createElement('div');
                    generatingDiv.className = 'generating';
                    generatingDiv.innerHTML = '<div class="spinner"></div> Generating...';
                    chatContainer.appendChild(generatingDiv);
                }
                
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                // Update send button state
                sendBtn.disabled = isGenerating;
                messageInput.disabled = isGenerating;
            }
        });
    </script>
</body>
</html>`;
    }
    
    public dispose() {
        this._client?.dispose();
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
