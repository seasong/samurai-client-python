from distutils.core import setup

from feefighters import version

setup(name='feefighters',
      version=version.Version,
      description="This is the python library for the Samurai API from Fee Fighters.",
      author='Samurai',
      author_email='Samurai@gmail.com.com',
      url="http://feefighters.com/samurai",
      packages=["feefighters", "feefighters.util"],
      provides=['FeeFighters'],
      keywords = ['pay', 'payment'],
      classifiers = [
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Linguistic",
        ],
      long_description = open('README').read()
      )
