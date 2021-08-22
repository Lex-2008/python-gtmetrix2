import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-gtmetrix2",
    version="0.0.1",
    author="Alexey Shpakovsky",
    author_email="alexey+setup.py@shpakovsky.ru",
    description="A Python client library for GTmetrix REST API v2.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Lex-2008/python-gtmetrix2",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.5",
)
