import re
import setuptools


README_FILENAME = "README.md"
VERSION_FILENAME = "observed.py"
VERSION_RE = r"^__version__ = ['\"]([^'\"]*)['\"]"


# Get version information
with open(VERSION_FILENAME, "rt") as version_file:
    mo = re.search(VERSION_RE, version_file.read(), re.M)

if mo:
    version = mo.group(1)
else:
    msg = "Unable to find version string in %s." % (version_file,)
    raise RuntimeError(msg)

# Get description information
with open(README_FILENAME, "rt") as description_file:
    long_description = description_file.read()

setuptools.setup(
    name='observed',
    version=version,
    author='Daniel Sank',
    author_email='sank.daniel@gmail.com',
    description='Observer pattern for functions and bound methods',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/DanielSank/observed',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
