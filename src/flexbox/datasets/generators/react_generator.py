"""React Dataset Generator - produces high-quality TypeScript/React training data."""

import json
from pathlib import Path
from typing import Optional

from ..curator import TrainingExample


SYSTEM_PROMPT = """You are a React/TypeScript specialist. Generate clean, functional React components with:
- Proper TypeScript interfaces and types
- Modern hooks (useState, useEffect, useContext, useMemo, useCallback, useRef)
- Functional component patterns
- Accessibility (ARIA) attributes when appropriate
- Clean, readable code structure

Output only the code. No explanations."""

# Curated React component templates
REACT_TEMPLATES = [
    # Basic Components
    {
        "prompt": "Create a Button component with variants and size options",
        "completion": '''import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

const variantClasses = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'bg-transparent text-gray-600 hover:bg-gray-100',
};

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  type = 'button',
}) => {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center
        font-medium rounded-lg transition-colors
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${sizeClasses[size]}
        ${variantClasses[variant]}
      `}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
};''',
    },
    # Input Component
    {
        "prompt": "Create an Input component with label, error state, and icon support",
        "completion": '''import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            className={`
              block w-full rounded-lg border transition-colors
              ${error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'}
              ${leftIcon ? 'pl-10' : 'pl-3'}
              ${rightIcon ? 'pr-10' : 'pr-3'}
              py-2 focus:outline-none focus:ring-2 focus:border-transparent
              disabled:bg-gray-50 disabled:text-gray-500
              ${className}
            `}
            {...props}
          />
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400">
              {rightIcon}
            </div>
          )}
        </div>
        {(error || helperText) && (
          <p className={`mt-1 text-sm ${error ? 'text-red-600' : 'text-gray-500'}`}>
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';''',
    },
    # Modal Component
    {
        "prompt": "Create a Modal component with close button and overlay",
        "completion": '''import React, { useEffect, useRef } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
}) => {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 overflow-y-auto"
      onClick={(e) => e.target === overlayRef.current && onClose()}
    >
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50 transition-opacity" />
        <div
          className={`
            relative w-full transform rounded-xl bg-white p-6 shadow-xl
            transition-all ${sizeClasses[size]}
          `}
        >
          {title && (
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500 focus:outline-none"
                aria-label="Close modal"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  );
};''',
    },
    # Custom Hooks
    {
        "prompt": "Create a useLocalStorage hook with TypeScript",
        "completion": '''import { useState, useEffect, useCallback } from 'react';

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void, () => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      if (typeof window === 'undefined') return initialValue;
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(valueToStore));
        }
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, storedValue]
  );

  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue);
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(key);
      }
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue]);

  return [storedValue, setValue, removeValue];
}''',
    },
    # Form Component
    {
        "prompt": "Create a Form component with validation and submit handling",
        "completion": '''import React, { FormEvent, ReactNode } from 'react';

interface FormProps {
  children: ReactNode;
  onSubmit: (e: FormEvent) => void;
  validation?: Record<string, string>;
  className?: string;
}

interface FieldProps {
  name: string;
  label: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}

export const Form: React.FC<FormProps> = ({
  children,
  onSubmit,
  className = '',
}) => {
  return (
    <form onSubmit={onSubmit} className={`space-y-4 ${className}`} noValidate>
      {children}
    </form>
  );
};

export const Field: React.FC<FieldProps> = ({
  name,
  label,
  error,
  required,
  children,
}) => {
  return (
    <div className="space-y-1">
      <label htmlFor={name} className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-sm text-red-600" role="alert">{error}</p>
      )}
    </div>
  );
};''',
    },
    # DataTable Component
    {
        "prompt": "Create a DataTable component with sorting and pagination",
        "completion": '''import React, { useState, useMemo } from 'react';

interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  pageSize?: number;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  pageSize = 10,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(0);

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const paginatedData = sortedData.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(data.length / pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => col.sortable && handleSort(col.key)}
                className={\`px-4 py-3 text-left text-sm font-semibold text-gray-900 \${
                  col.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }\`}
              >
                <span className="flex items-center gap-1">
                  {col.header}
                  {sortKey === col.key && (
                    <span>{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {paginatedData.map((item, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 text-sm text-gray-700">
                  {col.render ? col.render(item) : item[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-between bg-gray-50 px-4 py-3">
        <span className="text-sm text-gray-700">
          Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, data.length)} of {data.length}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}''',
    },
]


class ReactGenerator:
    """Generates React/TypeScript training examples."""

    def __init__(self, custom_templates: Optional[list[dict]] = None):
        self.templates = REACT_TEMPLATES.copy()
        if custom_templates:
            self.templates.extend(custom_templates)

    def generate(self) -> list[TrainingExample]:
        """Generate all React training examples."""
        examples = []
        
        for template in self.templates:
            example = TrainingExample(
                prompt=template["prompt"],
                completion=template["completion"],
                system_prompt=SYSTEM_PROMPT,
                metadata={"source": "react", "type": "component"},
            )
            examples.append(example)
        
        return examples

    def generate_with_variations(self, multiplier: int = 3) -> list[TrainingExample]:
        """Generate examples with prompt variations."""
        base_examples = self.generate()
        variations = []
        
        prefixes = [
            "Create a new",
            "Build a",
            "Implement a",
            "Write a",
            "Develop a",
        ]
        
        for example in base_examples:
            for i in range(multiplier):
                prefix = prefixes[i % len(prefixes)]
                variation = TrainingExample(
                    prompt=f"{prefix} {example.prompt.lower()}",
                    completion=example.completion,
                    system_prompt=SYSTEM_PROMPT,
                    metadata={
                        "source": "react",
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
                    metadata={"source": "react", "type": "custom"},
                )
                examples.append(example)
        
        return examples
