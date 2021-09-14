import setuptools
import os

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Note that $TRAVIS_TAG might be an empty string
version = os.environ.get("TRAVIS_TAG", "")
if version == "":
    version = "0.0." + os.environ.get("TRAVIS_BUILD_NUMBER", "0")

print("Releasing version " + version)

setuptools.setup(
    name="python-gtmetrix2",
    version=version,
    author="Alexey Shpakovsky",
    author_email="alexey+setup.py@shpakovsky.ru",
    description="A Python client library for GTmetrix REST API v2.0",
    keywords="python gtmetrix performance lighthouse pagespeed yslow",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/Lex-2008/python-gtmetrix2",
    project_urls={"Documentation": "https://python-gtmetrix2.readthedocs.io/"},
    classifiers=[
        # https://pypi.org/classifiers/
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.5",
)
