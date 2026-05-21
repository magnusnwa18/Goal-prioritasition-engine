from setuptools import setup, find_packages

setup(
    name="priorityos",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=13.0.0",
        "anthropic>=0.20.0",
    ],
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "priorityos=main:main",
        ],
    },
)
