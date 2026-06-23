from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="flexbox",
    version="0.2.0",
    description="Local-first AI coding assistant with LoRA adapter swapping",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Flex Box Team",
    author_email="flexbox@example.com",
    url="https://github.com/russzw/FlexBox",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.35.0",
        "peft>=0.6.0",
        "accelerate>=0.24.0",
        "aiohttp>=3.9.0",
        "bitsandbytes>=0.41.0",
        "datasets>=2.14.0",
        "trl>=0.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
        "web": [
            "aiohttp>=3.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "flexbox=flexbox.cli:main",
            "flexbox-server=flexbox.server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Code Generators",
    ],
    keywords="ai code-generation lora adapter vscode react css tailwind",
    project_urls={
        "Documentation": "https://github.com/russzw/FlexBox/tree/main/docs",
        "Source": "https://github.com/russzw/FlexBox",
        "Tracker": "https://github.com/russzw/FlexBox/issues",
    },
)
