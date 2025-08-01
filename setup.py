#!/usr/bin/env python3
"""
Setup script for CodegenCICD Dashboard
"""
from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from backend/requirements.txt
def read_requirements():
    requirements_path = os.path.join("backend", "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    return []

setup(
    name="codegencd",
    version="1.0.0",
    author="Zeeeepa",
    author_email="pixalana@pm.me",
    description="AI-Powered CI/CD Dashboard with Validation Pipeline",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Zeeeepa/CodegenCICD",
    project_urls={
        "Bug Tracker": "https://github.com/Zeeeepa/CodegenCICD/issues",
        "Documentation": "https://github.com/Zeeeepa/CodegenCICD#readme",
        "Source Code": "https://github.com/Zeeeepa/CodegenCICD",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=["backend", "backend.*"]),
    python_requires=">=3.9",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "requests>=2.31.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "codegen=codegen_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml", "*.json"],
        "backend": ["*.py", "*.sql"],
        "frontend": ["build/**/*", "public/**/*", "src/**/*"],
    },
    zip_safe=False,
    keywords="ci cd dashboard ai automation github codegen validation",
    platforms=["any"],
)
