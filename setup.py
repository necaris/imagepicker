import os

from setuptools import setup, find_packages


VERSION = "0.1"

setup(
    name='imagepicker',
    version=VERSION,
    description='ImagePicker for choosing images',
    long_description='',
    url='http://github.com/necaris/imagepicker',
    packages=find_packages(),
    # license specified by classifier
    author='Rami Chowdhury',
    author_email='rami.chowdhury@gmail.com',
    maintainer='Rami Chowdhury',
    maintainer_email='rami.chowdhury@gmail.com',
    # download_url=('http://github.com/necaris/cuid.py/tarball'
    #               '/v{}'.format(VERSION)),
    install_requires=[],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD Software License",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    entry_points={'console_scripts': ['imagepicker = imagepicker.main:main']},
)
