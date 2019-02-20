#!/usr/bin/env python

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

HERE = os.path.dirname(os.path.abspath(__file__))

setup(
    name="json-rpc-django",
    version="1.0.0",
    description=("A simple JSON-RPC implementation for Django. An extension of " 
                 "django-json-rpc by Samuel Sutch"),
    author="Rishikesh Jha",
    author_email="rishijha424@gmail.com",
    license="MIT",
    url="https://github.com/Rishi-jha/django-json-rpc",
    download_url="https://github.com/Rishi-jha/django-json-rpc",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment', 'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent', 'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Framework :: Django', 'Framework :: Django :: 1.4',
        'Framework :: Django :: 1.5', 'Framework :: Django :: 1.6',
        'Framework :: Django :: 1.7', 'Framework :: Django :: 1.8',
        'Framework :: Django :: 2.1',
    ],
    packages=['jsonrpc'],
    zip_safe=False,  # we include templates and tests
    install_requires=['Django>=2.0', 'six'],
    package_data={'jsonrpc': ['templates/*']})
