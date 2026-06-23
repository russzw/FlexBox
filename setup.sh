#!/bin/bash
# Flex Box - One-click dependency installer
# Run this after cloning to set up the environment

set -e

echo "========================================="
echo "  Flex Box - Environment Setup"
echo "========================================="
echo ""

# Check Python version
python_version=$(python --version 2>&1)
echo "Python: $python_version"

echo ""
echo "Step 1: Installing PyTorch (CPU)..."
echo "  This downloads ~123MB and may take a few minutes."
pip install torch --timeout 3000

echo ""
echo "Step 2: Installing transformers and PEFT stack..."
pip install transformers peft accelerate sentencepiece protobuf

echo ""
echo "Step 3: Installing Flex Box in editable mode..."
pip install -e .

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Usage:"
echo "  flexbox route 'Create a React button component'"
echo "  flexbox generate 'Add bg-blue-500 text-white p-4'"
echo "  flexbox adapters"
echo "  flexbox info"
echo ""
echo "Run tests:"
echo "  python tests/test_phase1.py"
