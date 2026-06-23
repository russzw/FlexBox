import * as vscode from 'vscode';

export class DiffPanel {
    public static readonly viewType = 'flexbox.diff';
    
    private _panel?: vscode.WebviewPanel;
    private _content: string = '';
    private _filePath: string = '';
    
    constructor(private readonly _extensionUri: vscode.Uri) {}
    
    public show() {
        if (this._panel) {
            this._panel.reveal(vscode.ViewColumn.One);
            return;
        }
        
        this._panel = vscode.window.createWebviewPanel(
            DiffPanel.viewType,
            'Flex Box Diff',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [this._extensionUri],
            }
        );
        
        this._panel.webview.html = this._getHtmlForWebview(
            this._panel.webview,
            '',
            '',
            ''
        );
        
        this._panel.onDidDispose(
            () => { this._panel = undefined; },
            null,
            []
        );
        
        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.type) {
                    case 'apply':
                        await this._applyChanges(message.content);
                        break;
                    case 'reject':
                        this._panel?.dispose();
                        break;
                    case 'copy':
                        await vscode.env.clipboard.writeText(message.content);
                        vscode.window.showInformationMessage('Copied to clipboard');
                        break;
                }
            },
            undefined,
            []
        );
    }
    
    public showWithDiff(original: string, modified: string, filePath: string) {
        this._content = modified;
        this._filePath = filePath;
        
        if (!this._panel) {
            this.show();
        }
        
        if (this._panel) {
            this._panel.webview.html = this._getHtmlForWebview(
                this._panel.webview,
                original,
                modified,
                filePath
            );
            this._panel.reveal(vscode.ViewColumn.One);
        }
    }
    
    public getContent(uri: vscode.Uri): string {
        return this._content;
    }
    
    private async _applyChanges(content: string) {
        const editor = vscode.window.activeTextEditor;
        
        if (editor) {
            const fullRange = new vscode.Range(
                editor.document.positionAt(0),
                editor.document.positionAt(editor.document.getText().length)
            );
            
            await editor.edit(editBuilder => {
                editBuilder.replace(fullRange, content);
            });
            
            vscode.window.showInformationMessage('Flex Box: Changes applied');
            this._panel?.dispose();
        } else {
            // Save to file
            if (this._filePath) {
                const uri = vscode.Uri.file(this._filePath);
                await vscode.workspace.fs.writeFile(
                    uri,
                    Buffer.from(content, 'utf-8')
                );
                vscode.window.showInformationMessage(`Flex Box: Changes saved to ${this._filePath}`);
                this._panel?.dispose();
            }
        }
    }
    
    private _getHtmlForWebview(
        webview: vscode.Webview,
        original: string,
        modified: string,
        filePath: string
    ): string {
        const nonce = getNonce();
        
        // Escape HTML entities
        const escapeHtml = (text: string) => {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        };
        
        // Simple diff highlighting
        const highlightDiff = (orig: string, mod: string) => {
            const origLines = orig.split('\n');
            const modLines = mod.split('\n');
            
            let origHtml = '';
            let modHtml = '';
            
            const maxLines = Math.max(origLines.length, modLines.length);
            
            for (let i = 0; i < maxLines; i++) {
                const origLine = origLines[i] || '';
                const modLine = modLines[i] || '';
                
                if (origLine === modLine) {
                    origHtml += `<div class="line unchanged"><span class="line-num">${i + 1}</span>${escapeHtml(origLine)}</div>`;
                    modHtml += `<div class="line unchanged"><span class="line-num">${i + 1}</span>${escapeHtml(modLine)}</div>`;
                } else {
                    if (origLine) {
                        origHtml += `<div class="line removed"><span class="line-num">${i + 1}</span>${escapeHtml(origLine)}</div>`;
                    }
                    if (modLine) {
                        modHtml += `<div class="line added"><span class="line-num">${i + 1}</span>${escapeHtml(modLine)}</div>`;
                    }
                }
            }
            
            return { origHtml, modHtml };
        };
        
        const { origHtml, modHtml } = highlightDiff(original, modified);
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <title>Flex Box Diff</title>
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
            background: var(--vscode-editor-background);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: var(--vscode-sideBar-background);
            border-bottom: 1px solid var(--vscode-widget-border);
        }
        
        .header h2 {
            font-size: 14px;
            font-weight: 600;
        }
        
        .header .file-path {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        
        .toolbar {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            background: var(--vscode-sideBar-background);
            border-bottom: 1px solid var(--vscode-widget-border);
        }
        
        .toolbar button {
            padding: 6px 12px;
            font-size: 12px;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .btn-apply {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
        }
        
        .btn-apply:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .btn-reject {
            background: transparent;
            color: var(--vscode-foreground);
            border: 1px solid var(--vscode-widget-border);
        }
        
        .btn-reject:hover {
            background: var(--vscode-editor-hoverHighlightBackground);
        }
        
        .btn-copy {
            background: transparent;
            color: var(--vscode-foreground);
            border: 1px solid var(--vscode-widget-border);
        }
        
        .diff-container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        
        .diff-panel {
            flex: 1;
            overflow-y: auto;
            border-right: 1px solid var(--vscode-widget-border);
        }
        
        .diff-panel:last-child {
            border-right: none;
        }
        
        .diff-panel-header {
            position: sticky;
            top: 0;
            padding: 8px 16px;
            background: var(--vscode-sideBar-background);
            border-bottom: 1px solid var(--vscode-widget-border);
            font-size: 12px;
            font-weight: 600;
            z-index: 1;
        }
        
        .line {
            display: flex;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            line-height: 20px;
            padding: 0 16px;
        }
        
        .line-num {
            width: 40px;
            text-align: right;
            padding-right: 12px;
            color: var(--vscode lineNumber.foreground);
            user-select: none;
        }
        
        .line.unchanged {
            background: transparent;
        }
        
        .line.added {
            background: rgba(46, 160, 67, 0.2);
            border-left: 3px solid #2ea043;
        }
        
        .line.removed {
            background: rgba(248, 81, 73, 0.2);
            border-left: 3px solid #f85149;
        }
        
        .stats {
            padding: 12px 16px;
            background: var(--vscode-sideBar-background);
            border-top: 1px solid var(--vscode-widget-border);
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        
        .stats span {
            margin-right: 16px;
        }
        
        .added-count {
            color: #2ea043;
        }
        
        .removed-count {
            color: #f85149;
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h2>Flex Box Diff</h2>
            ${filePath ? `<div class="file-path">${escapeHtml(filePath)}</div>` : ''}
        </div>
    </div>
    
    <div class="toolbar">
        <button class="btn-apply" onclick="applyChanges()">Apply Changes</button>
        <button class="btn-reject" onclick="rejectChanges()">Reject</button>
        <button class="btn-copy" onclick="copyChanges()">Copy to Clipboard</button>
    </div>
    
    <div class="diff-container">
        <div class="diff-panel">
            <div class="diff-panel-header">Original</div>
            ${origHtml || '<div class="line unchanged"><span class="line-num">1</span>No original content</div>'}
        </div>
        <div class="diff-panel">
            <div class="diff-panel-header">Modified</div>
            ${modHtml || '<div class="line unchanged"><span class="line-num">1</span>No modified content</div>'}
        </div>
    </div>
    
    <div class="stats">
        <span class="added-count">+${modified.split('\n').length} lines</span>
        <span class="removed-count">-${original.split('\n').length} lines</span>
    </div>
    
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const modifiedContent = ${JSON.stringify(modified)};
        
        function applyChanges() {
            vscode.postMessage({ type: 'apply', content: modifiedContent });
        }
        
        function rejectChanges() {
            vscode.postMessage({ type: 'reject' });
        }
        
        function copyChanges() {
            vscode.postMessage({ type: 'copy', content: modifiedContent });
        }
    </script>
</body>
</html>`;
    }
    
    public dispose() {
        this._panel?.dispose();
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
