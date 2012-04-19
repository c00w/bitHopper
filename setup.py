import os
from setuptools import setup

setup(
    name = "dummy_bithopper_install",
    version = "0.0.4",
    description = ("A dummy package to install things correctly for bitHopper"),
    install_requires=[
		'setuptools',
		'gitpython',
		'httplib2'
	],
)