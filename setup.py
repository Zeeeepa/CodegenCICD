#!/usr/bin/env python3
"""
Setup script for CodegenCICD Dashboard
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "CodegenCICD Dashboard - A comprehensive CICD dashboard for GitHub projects"

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'backend', 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="codegencd",
    version="1.0.0",
    description="CodegenCICD Dashboard - A comprehensive CICD dashboard for GitHub projects",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Zeeeepa",
    author_email="pixalana@pm.me",
    url="https://github.com/Zeeeepa/CodegenCICD",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'codegen=codegen_cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Tools",
        "Topic :: System :: Software Distribution",
    ],
    keywords="cicd dashboard github automation codegen",
    project_urls={
        "Bug Reports": "https://github.com/Zeeeepa/CodegenCICD/issues",
        "Source": "https://github.com/Zeeeepa/CodegenCICD",
        "Documentation": "https://github.com/Zeeeepa/CodegenCICD/blob/main/README.md",
    },
)

