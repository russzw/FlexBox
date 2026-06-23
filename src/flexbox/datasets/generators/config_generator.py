"""Config Dataset Generator - produces configuration file training data."""

import json
from pathlib import Path
from typing import Optional

from ..curator import TrainingExample


SYSTEM_PROMPT = """You are a configuration specialist. Generate valid, properly formatted:
- JSON/YAML/TOML configuration files
- Environment variable files (.env)
- Build tool configs (webpack, vite, rollup)
- Package manifests (package.json, pyproject.toml)
- TypeScript/JavaScript configs

Output only the code. No explanations."""

CONFIG_TEMPLATES = [
    # Next.js Config
    {
        "prompt": "Create a Next.js project configuration with TypeScript and Tailwind",
        "completion": '''{
  "name": "my-nextjs-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest",
    "test:watch": "jest --watch"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "eslint": "^8",
    "eslint-config-next": "14.2.0",
    "postcss": "^8",
    "tailwindcss": "^3.3.0",
    "typescript": "^5"
  }
}''',
    },
    # Vite Config
    {
        "prompt": "Configure Vite with React, path aliases, and proxy",
        "completion": '''import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@styles': path.resolve(__dirname, './src/styles'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
        },
      },
    },
  },
});''',
    },
    # TypeScript Config
    {
        "prompt": "Create a strict TypeScript configuration with path aliases",
        "completion": '''{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@utils/*": ["./src/utils/*"],
      "@hooks/*": ["./src/hooks/*"],
      "@styles/*": ["./src/styles/*"],
      "@assets/*": ["./src/assets/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}''',
    },
    # Tailwind Config
    {
        "prompt": "Create a Tailwind CSS configuration with custom theme",
        "completion": '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};''',
    },
    # Environment Variables
    {
        "prompt": "Create environment variables for a full-stack app",
        "completion": '''# App Configuration
NEXT_PUBLIC_APP_NAME=MyApp
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_APP_URL=http://localhost:3000

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8080/api
NEXT_PUBLIC_API_TIMEOUT=30000

# Authentication
NEXT_PUBLIC_AUTH_DOMAIN=auth.example.com
NEXT_PUBLIC_AUTH_CLIENT_ID=your-client-id
NEXT_PUBLIC_AUTH_REDIRECT_URI=http://localhost:3000/callback

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://localhost:6379

# Email Service
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASS=your-smtp-password

# Storage
S3_BUCKET=my-app-bucket
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
NEXT_PUBLIC_ENABLE_BETA_FEATURES=false

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=info''',
    },
    # Webpack Config
    {
        "prompt": "Configure webpack with loaders and plugins",
        "completion": '''const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  entry: './src/index.tsx',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'static/js/[name].[contenthash:8].js',
    publicPath: '/',
    clean: true,
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js', '.jsx'],
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  module: {
    rules: [
      {
        test: /\\.(ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              '@babel/preset-env',
              '@babel/preset-react',
              '@babel/preset-typescript',
            ],
          },
        },
      },
      {
        test: /\\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader', 'postcss-loader'],
      },
      {
        test: /\\.(png|svg|jpg|jpeg|gif|webp)$/,
        type: 'asset/resource',
        generator: {
          filename: 'static/images/[name].[hash][ext]',
        },
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html',
    }),
    new MiniCssExtractPlugin({
      filename: 'static/css/[name].[contenthash:8].css',
    }),
  ],
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\\\/]node_modules[\\\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
      },
    },
  },
};''',
    },
]


class ConfigGenerator:
    """Generates configuration file training examples."""

    def __init__(self, custom_templates: Optional[list[dict]] = None):
        self.templates = CONFIG_TEMPLATES.copy()
        if custom_templates:
            self.templates.extend(custom_templates)

    def generate(self) -> list[TrainingExample]:
        """Generate all config training examples."""
        examples = []
        
        for template in self.templates:
            example = TrainingExample(
                prompt=template["prompt"],
                completion=template["completion"],
                system_prompt=SYSTEM_PROMPT,
                metadata={"source": "config", "type": "configuration"},
            )
            examples.append(example)
        
        return examples

    def generate_with_variations(self, multiplier: int = 3) -> list[TrainingExample]:
        """Generate examples with prompt variations."""
        base_examples = self.generate()
        variations = []
        
        prefixes = [
            "Create a",
            "Set up a",
            "Configure a",
            "Initialize a",
            "Write a",
        ]
        
        for example in base_examples:
            for i in range(multiplier):
                prefix = prefixes[i % len(prefixes)]
                variation = TrainingExample(
                    prompt=f"{prefix} {example.prompt.lower().replace('create a ', '').replace('configure a ', '').replace('set up a ', '')}",
                    completion=example.completion,
                    system_prompt=SYSTEM_PROMPT,
                    metadata={
                        "source": "config",
                        "type": "variation",
                        "base_prompt": example.prompt,
                    },
                )
                variations.append(variation)
        
        return base_examples + variations

    def load_from_file(self, filepath: str) -> list[TrainingExample]:
        """Load additional templates from a JSONL file."""
        examples = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                example = TrainingExample(
                    prompt=data["prompt"],
                    completion=data["completion"],
                    system_prompt=data.get("system_prompt", SYSTEM_PROMPT),
                    metadata={"source": "config", "type": "custom"},
                )
                examples.append(example)
        
        return examples
