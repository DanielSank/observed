# Get version information
import re
version_file = "observed/_version.py"
verstrline = open(version_file, "rt").read()
version_re = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(version_re, verstrline, re.M)
if mo:
    version = mo.group(1)
else:
    msg = "Unable to find version string in %s." % (version_file,)
    raise RuntimeError(msg)

from distutils.core import setup

setup(name='observed',
      packages = ['observed'],
      version = version,
      description='Observer pattern for functions and bound methods',
      author='Daniel Sank',
      author_email='sank.daniel@gmail.com',
      url='https://github.com/DanielSank/observed',
      download_url='https://github.com/DanielSank/observed/tarball/'+version,
      keywords=['observer', 'event', 'callback'],
      classifiers=[],
)
