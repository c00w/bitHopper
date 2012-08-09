"""
Dummy file to install bitHopper dependencies
"""
from setuptools import setup

setup(
    name = "dummy_bithopper_install",
    version = "0.0.8",
    description = ("A dummy package to install things correctly for bitHopper"),
    install_requires=[
		'setuptools',
		'requests',
		'mechanize',
		'gevent>=0.13.7',
		'btcnet_info>=0.1.2.22',
		'flask',
	],
)
