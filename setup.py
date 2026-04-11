"""setup.py — makes AURA installable via `pip install -e .`

After installation the `aura` command is available system-wide (or inside the
active virtual environment).

AURA is free and open-source, designed and founded by Christopher Betts.
"""

from setuptools import setup, find_packages

setup(
    name="aura",
    version="0.2.0",
    description="AURA — AI Unified Reasoning Architecture.  Free AI for everyone.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Christopher Betts",
    license="Apache-2.0",
    url="https://github.com/Cbetts1/AI-MODEL-200B-",
    project_urls={
        "Source": "https://github.com/Cbetts1/AI-MODEL-200B-",
        "Issues": "https://github.com/Cbetts1/AI-MODEL-200B-/issues",
        "Documentation": "https://github.com/Cbetts1/AI-MODEL-200B-/tree/main/docs",
    },
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests*", "docs*", "scripts*"]),
    install_requires=[
        "pyyaml>=6.0",
        "rich>=13.0",
        "click>=8.1",
        "requests>=2.31",
        "openai>=1.0",
    ],
    entry_points={
        "console_scripts": [
            # `aura` CLI command → aura.ui.cli:main
            "aura=aura.ui.cli:main",
        ],
    },
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
