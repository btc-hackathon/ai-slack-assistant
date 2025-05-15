import os
from typing import List

from setuptools import setup

ROOT_DIR = os.path.dirname(__file__)


def get_path(*filepath) -> str:
    return os.path.join(ROOT_DIR, *filepath)


def get_requirements(filename: str) -> List[str]:
    with open(get_path(filename)) as f:
        requirements = f.read().strip().split("\n")
    resolved_requirements = []
    for line in requirements:
        if line.startswith("-r "):
            resolved_requirements += get_requirements(line.split()[1])
        else:
            resolved_requirements.append(line)
    return resolved_requirements


setup(
    name="ai_slack_assistant",
    version="0.1.0",
    description="An AI-powered Slack bot to help with daily work tasks",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Vaibhav Jain",
    author_email="vajain@redhat.com",
    url="https://github.com/btc-hackathon/ai-slack-assistant",
    license="MIT",
    package_dir = {'': 'src'},
    python_requires=">=3.8",
    install_requires=get_requirements("requirements.txt"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
