from setuptools import setup
import os
import sys


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


extra = {}
requirements = ['distribute', 'docutils', 'requests'],
tests_require = ['nose', 'coverage', 'Mock']

# In case we use python3
if sys.version_info >= (3,):
    extra['use_2to3'] = True

if sys.version_info <= (2, 6):
    requirements.append('simplejson')

setup(
    name="docar",
    version="0.4.1",
    packages=['docar', 'docar.backends'],
    include_package_data=True,
    #zip_safe=False,  # Don't create egg files, Django cannot find templates
                     # in egg files.
    install_requires=requirements,
    tests_require=tests_require,
    setup_requires='nose',
    test_suite="nose.collector",
    extras_require={'test': tests_require},

    author="Christo Buschek",
    author_email="crito@30loops.net",
    url="https://github.com/30loops/python-docar",
    description="Create resource oriented architectures for RESTful client \
and server applications.",
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    **extra
)
