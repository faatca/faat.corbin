import os
import io
import re
from setuptools import setup


def read(*names, **kwargs):
    path = os.path.join(os.path.dirname(__file__), *names)
    with io.open(path, encoding=kwargs.get("encoding", "utf8")) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="faat.corbin",
    version=find_version("faat", "corbin", "__init__.py"),
    description="Simplified framework for AMQP workers",
    long_description=read("README.md"),
    url="https://faat.ca",
    author="Aaron Milner",
    author_email="aaron.milner@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="",
    packages=["faat.corbin"],
    install_requires=["pika>=1.1.0"],
    python_requires=">=3.8",
)
