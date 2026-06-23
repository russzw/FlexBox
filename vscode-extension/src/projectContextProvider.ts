import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface ProjectInfo {
    framework: string;
    styling: string;
    language: string;
    fileCount: number;
    componentCount: number;
    styleCount: number;
    configCount: number;
}

export class ProjectContextProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'flexbox.context';
    
    private _view?: vscode.WebviewView;
    private _watcher?: fs.FSWatcher;
    private _projectInfo: ProjectInfo = {
        framework: 'unknown',
        styling: 'unknown',
        language: 'unknown',
        fileCount: 0,
        componentCount: 0,
        styleCount: 0,
        configCount: 0,
    };
    
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
        
        // Initial scan
        this.scanProject();
    }
    
    public startWatching() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return;
        }
        
        const rootPath = workspaceFolders[0].uri.fsPath;
        
        // Watch for file changes
        this._watcher = fs.watch(
            rootPath,
            { recursive: true },
            (eventType, filename) => {
                if (filename) {
                    this.scanProject();
                }
            }
        );
    }
    
    public stopWatching() {
        if (this._watcher) {
            this._watcher.close();
            this._watcher = undefined;
        }
    }
    
    public clear() {
        this._projectInfo = {
            framework: 'unknown',
            styling: 'unknown',
            language: 'unknown',
            fileCount: 0,
            componentCount: 0,
            styleCount: 0,
            configCount: 0,
        };
        this._updateWebview();
    }
    
    public refresh() {
        this.scanProject();
    }
    
    private scanProject() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return;
        }
        
        const rootPath = workspaceFolders[0].uri.fsPath;
        
        const info: ProjectInfo = {
            framework: 'unknown',
            styling: 'unknown',
            language: 'unknown',
            fileCount: 0,
            componentCount: 0,
            styleCount: 0,
            configCount: 0,
        };
        
        // Detect framework
        if (fs.existsSync(path.join(rootPath, 'next.config.js')) ||
            fs.existsSync(path.join(rootPath, 'next.config.mjs')) ||
            fs.existsSync(path.join(rootPath, 'next.config.ts'))) {
            info.framework = 'Next.js';
        } else if (fs.existsSync(path.join(rootPath, 'vite.config.js')) ||
                   fs.existsSync(path.join(rootPath, 'vite.config.ts'))) {
            info.framework = 'Vite';
        } else if (fs.existsSync(path.join(rootPath, 'vue.config.js'))) {
            info.framework = 'Vue';
        } else if (fs.existsSync(path.join(rootPath, 'angular.json'))) {
            info.framework = 'Angular';
        } else if (fs.existsSync(path.join(rootPath, 'svelte.config.js'))) {
            info.framework = 'Svelte';
        }
        
        // Detect styling
        if (fs.existsSync(path.join(rootPath, 'tailwind.config.js')) ||
            fs.existsSync(path.join(rootPath, 'tailwind.config.ts'))) {
            info.styling = 'Tailwind CSS';
        } else if (fs.existsSync(path.join(rootPath, 'postcss.config.js'))) {
            info.styling = 'PostCSS';
        }
        
        // Count files
        const countFiles = (dir: string) => {
            try {
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                
                for (const entry of entries) {
                    const fullPath = path.join(dir, entry.name);
                    
                    if (entry.name === 'node_modules' || entry.name === '.git' || entry.name === 'dist') {
                        continue;
                    }
                    
                    if (entry.isDirectory()) {
                        countFiles(fullPath);
                    } else {
                        info.fileCount++;
                        
                        const ext = path.extname(entry.name).toLowerCase();
                        
                        if (['.jsx', '.tsx', '.vue', '.svelte'].includes(ext)) {
                            info.componentCount++;
                        }
                        
                        if (['.css', '.scss', '.less', '.module.css'].includes(ext)) {
                            info.styleCount++;
                        }
                        
                        if (ext === '.json' || entry.name.includes('config')) {
                            info.configCount++;
                        }
                        
                        // Detect language
                        if (ext === '.ts' || ext === '.tsx') {
                            info.language = 'TypeScript';
                        } else if (ext === '.js' || ext === '.jsx') {
                            if (info.language !== 'TypeScript') {
                                info.language = 'JavaScript';
                            }
                        }
                    }
                }
            } catch (e) {
                // Ignore permission errors
            }
        };
        
        countFiles(rootPath);
        
        this._projectInfo = info;
        this._updateWebview();
    }
    
    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'updateInfo',
                info: this._projectInfo,
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
    <title>Project Context</title>
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
            padding: 12px;
        }
        
        .section {
            margin-bottom: 16px;
        }
        
        .section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .info-item {
            background: var(--vscode-editor-background);
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid var(--vscode-widget-border);
        }
        
        .info-label {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 2px;
        }
        
        .info-value {
            font-size: 13px;
            font-weight: 500;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }
        
        .stat-item {
            background: var(--vscode-editor-background);
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid var(--vscode-widget-border);
            text-align: center;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: var(--vscode-textLink-foreground);
        }
        
        .stat-label {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 2px;
        }
        
        .unknown {
            color: var(--vscode-descriptionForeground);
            font-style: italic;
        }
        
        .toolbar {
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
        }
        
        .toolbar button {
            flex: 1;
            padding: 6px 8px;
            font-size: 11px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .toolbar button:hover {
            background: var(--vscode-button-hoverBackground);
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <button onclick="refresh()">Refresh</button>
        <button onclick="clearContext()">Clear</button>
    </div>
    
    <div class="section">
        <div class="section-title">Project Info</div>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Framework</div>
                <div class="info-value" id="framework">Loading...</div>
            </div>
            <div class="info-item">
                <div class="info-label">Styling</div>
                <div class="info-value" id="styling">Loading...</div>
            </div>
            <div class="info-item">
                <div class="info-label">Language</div>
                <div class="info-value" id="language">Loading...</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">File Statistics</div>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="fileCount">0</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="componentCount">0</div>
                <div class="stat-label">Components</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="styleCount">0</div>
                <div class="stat-label">Styles</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="configCount">0</div>
                <div class="stat-label">Configs</div>
            </div>
        </div>
    </div>
    
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        
        function refresh() {
            vscode.postMessage({ type: 'refresh' });
        }
        
        function clearContext() {
            vscode.postMessage({ type: 'clear' });
        }
        
        function updateInfo(info) {
            document.getElementById('framework').textContent = info.framework;
            document.getElementById('styling').textContent = info.styling;
            document.getElementById('language').textContent = info.language;
            document.getElementById('fileCount').textContent = info.fileCount;
            document.getElementById('componentCount').textContent = info.componentCount;
            document.getElementById('styleCount').textContent = info.styleCount;
            document.getElementById('configCount').textContent = info.configCount;
            
            // Style unknown values
            ['framework', 'styling', 'language'].forEach(id => {
                const el = document.getElementById(id);
                if (el.textContent === 'unknown') {
                    el.classList.add('unknown');
                } else {
                    el.classList.remove('unknown');
                }
            });
        }
        
        window.addEventListener('message', (event) => {
            const { type, info } = event.data;
            
            if (type === 'updateInfo') {
                updateInfo(info);
            }
        });
    </script>
</body>
</html>`;
    }
    
    public dispose() {
        this.stopWatching();
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
