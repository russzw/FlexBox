from setuptools import setup, find_packages

setup(
    name="flexbox",
    version="0.1.0",
    description="Local-first multi-agent development environment with LoRA swapping",
    author="Flex Box Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.35.0",
        "peft>=0.6.0",
        "accelerate>=0.24.0",
    ],
    entry_points={
        "console_scripts": [
            "flexbox=flexbox.cli:main",
        ],
    },
)
