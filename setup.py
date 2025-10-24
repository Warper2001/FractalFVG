"""
Setup script for unified deployment script
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="unified-deployment-script",
    version="1.0.0",
    author="FractalFVG",
    description="Unified deployment script for QuantConnect algorithms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FractalFVG/FractalFVG",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.31.0",
        "click>=8.1.0", 
        "python-dotenv>=1.0.0",
        "tqdm>=4.66.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "deploy-unified=deploy_unified:main",
        ],
    },
)