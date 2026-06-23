import * as vscode from 'vscode';
import { FlexBoxChatProvider } from './flexboxChatProvider';
import { DiffPanel } from './diffPanel';
import { ProjectContextProvider } from './projectContextProvider';

let chatProvider: FlexBoxChatProvider;
let diffPanel: DiffPanel;
let contextProvider: ProjectContextProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('Flex Box extension activating...');
    
    // Initialize providers
    chatProvider = new FlexBoxChatProvider(context.extensionUri);
    diffPanel = new DiffPanel(context.extensionUri);
    contextProvider = new ProjectContextProvider(context.extensionUri);
    
    // Register webview providers
    const chatViewProvider = vscode.window.registerWebviewViewProvider(
        'flexbox.chat',
        chatProvider,
        { webviewOptions: { retainContextWhenHidden: true } }
    );
    
    const contextViewProvider = vscode.window.registerWebviewViewProvider(
        'flexbox.context',
        contextProvider,
        { webviewOptions: { retainContextWhenHidden: true } }
    );
    
    // Register commands
    const openChatCmd = vscode.commands.registerCommand(
        'flexbox.openChat',
        () => chatProvider.show()
    );
    
    const generateCodeCmd = vscode.commands.registerCommand(
        'flexbox.generateCode',
        () => handleGenerateCode(context)
    );
    
    const openDiffCmd = vscode.commands.registerCommand(
        'flexbox.openDiff',
        () => diffPanel.show()
    );
    
    const clearContextCmd = vscode.commands.registerCommand(
        'flexbox.clearContext',
        () => {
            contextProvider.clear();
            vscode.window.showInformationMessage('Flex Box: Context cleared');
        }
    );
    
    const refreshMemoryCmd = vscode.commands.registerCommand(
        'flexbox.refreshMemory',
        () => {
            contextProvider.refresh();
            vscode.window.showInformationMessage('Flex Box: Project memory refreshed');
        }
    );
    
    // Register content provider for inline diffs
    const contentProvider = vscode.workspace.registerTextDocumentContentProvider(
        'flexbox',
        {
            provideTextDocumentContent(uri: vscode.Uri): string {
                return diffPanel.getContent(uri);
            }
        }
    );
    
    // Add to subscriptions
    context.subscriptions.push(
        chatViewProvider,
        contextViewProvider,
        openChatCmd,
        generateCodeCmd,
        openDiffCmd,
        clearContextCmd,
        refreshMemoryCmd,
        contentProvider
    );
    
    // Start project memory watcher
    contextProvider.startWatching();
    
    console.log('Flex Box extension activated');
}

export function deactivate() {
    console.log('Flex Box extension deactivating...');
    
    if (contextProvider) {
        contextProvider.stopWatching();
    }
    
    if (chatProvider) {
        chatProvider.dispose();
    }
    
    if (diffPanel) {
        diffPanel.dispose();
    }
}

async function handleGenerateCode(context: vscode.ExtensionContext) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }
    
    // Get selected text or prompt user
    const selection = editor.document.getText(editor.selection);
    let prompt: string;
    
    if (selection) {
        prompt = await vscode.window.showInputBox({
            prompt: 'Describe what to do with the selection',
            placeHolder: 'e.g., "Add error handling" or "Convert to TypeScript"',
            value: selection.substring(0, 100),
        }) || '';
    } else {
        prompt = await vscode.window.showInputBox({
            prompt: 'What would you like to generate?',
            placeHolder: 'e.g., "Create a React button component"',
        }) || '';
    }
    
    if (!prompt) {
        return;
    }
    
    // Show progress
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Flex Box',
        cancellable: true,
    }, async (progress, token) => {
        progress.report({ message: 'Generating code...' });
        
        try {
            // In production, this would call the Flex Box backend
            // For now, show a placeholder
            const result = await simulateGeneration(prompt, editor.document.languageId);
            
            // Show diff panel with result
            diffPanel.showWithDiff(
                editor.document.getText(),
                result,
                editor.document.fileName
            );
            
        } catch (error: any) {
            vscode.window.showErrorMessage(`Flex Box: ${error.message}`);
        }
    });
}

async function simulateGeneration(prompt: string, languageId: string): Promise<string> {
    // Simulate code generation
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const templates: Record<string, string> = {
        'typescriptreact': `import React from 'react';

interface ComponentProps {
  // Add props here
}

export const GeneratedComponent: React.FC<ComponentProps> = (props) => {
  return (
    <div>
      {/* Generated from: ${prompt} */}
      <p>Component placeholder</p>
    </div>
  );
};`,
        'typescript': `// Generated from: ${prompt}
export function generatedFunction(): void {
    // Implementation here
    console.log('Generated code');
}`,
        'css': `/* Generated from: ${prompt} */
.generated-class {
    display: flex;
    align-items: center;
    padding: 1rem;
}`,
    };
    
    return templates[languageId] || templates['typescript'];
}
