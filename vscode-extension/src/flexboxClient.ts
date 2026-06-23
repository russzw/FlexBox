import * as vscode from 'vscode';
import * as http from 'http';

const API_BASE = 'http://127.0.0.1:8181';

interface GenerateResponse {
    text: string;
    adapter_used: string;
    tokens_generated: number;
    latency_ms: number;
}

interface RouteResponse {
    primary_adapter: string;
    subtasks: any[];
    multi_adapter: boolean;
}

interface AdaptersResponse {
    adapters: Record<string, { path: string }>;
}

export class FlexBoxClient {
    private _outputChannel: vscode.OutputChannel;

    constructor() {
        this._outputChannel = vscode.window.createOutputChannel('Flex Box');
    }

    async isServerRunning(): Promise<boolean> {
        try {
            await this._request('GET', '/health');
            return true;
        } catch {
            return false;
        }
    }

    async generate(
        prompt: string,
        adapter?: string,
        systemPrompt?: string,
        maxTokens?: number
    ): Promise<GenerateResponse> {
        return this._request('POST', '/api/v1/generate', {
            prompt,
            adapter,
            system_prompt: systemPrompt,
            max_tokens: maxTokens,
        });
    }

    async route(prompt: string): Promise<RouteResponse> {
        return this._request('POST', '/api/v1/route', { prompt });
    }

    async getAdapters(): Promise<AdaptersResponse> {
        return this._request('GET', '/api/v1/adapters');
    }

    async getContext(): Promise<{ context: string }> {
        return this._request('GET', '/api/v1/context');
    }

    async healthCheck(): Promise<any> {
        return this._request('GET', '/health');
    }

    private _request<T>(method: string, path: string, body?: any): Promise<T> {
        return new Promise((resolve, reject) => {
            const url = new URL(path, API_BASE);
            const options: http.RequestOptions = {
                hostname: url.hostname,
                port: url.port,
                path: url.pathname,
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        reject(new Error(`Invalid JSON response: ${data}`));
                    }
                });
            });

            req.on('error', (err) => {
                reject(new Error(`Connection failed: ${err.message}`));
            });

            req.setTimeout(120000, () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });

            if (body) {
                req.write(JSON.stringify(body));
            }
            req.end();
        });
    }

    log(message: string) {
        this._outputChannel.appendLine(message);
    }

    dispose() {
        this._outputChannel.dispose();
    }
}
