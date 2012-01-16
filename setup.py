from setuptools import setup, find_packages
import os
import sys


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


extra = {}
requirements = ['distribute', 'docutils'],
tests_require = ['nose', 'coverage', 'Mock']

# In case we use python3
if sys.version_info >= (3,):
    extra['use_2to3'] = True

if sys.version_info <= (2, 6):
    requirements.append('simplejson')

setup(
    name="docar",
    version="0.1",
    packages=find_packages('src'),
    package_dir={'': 'src'},
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
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    **extra
)
