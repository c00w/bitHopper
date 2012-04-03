import os
from setuptools import setup

setup(
    name = "dummy_bithopper_install",
    version = "0.0.5",
    description = ("A dummy package to install things correctly for bitHopper"),
    install_requires=[
		'setuptools',
		'httplib2',
		'mechanize',
		'gevent',
		'btcnet_info',
		'flask',
	],
)
