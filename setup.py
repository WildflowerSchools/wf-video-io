import os
from setuptools import setup, find_packages

BASEDIR = os.path.dirname(os.path.abspath(__file__))
VERSION = open(os.path.join(BASEDIR, 'VERSION')).read().strip()

# Dependencies (format is 'PYPI_PACKAGE_NAME[>=]=VERSION_NUMBER')
BASE_DEPENDENCIES = [
    'wf-honeycomb_io>=0.2.0',
    'wf-cv-utils>=2.0.0',
    'opencv-python>=4.5.1',
    'jmespath',
    'tenacity',
    'wf_fastapi_auth0>=1.0',
]

TEST_DEPENDENCIES = [
    'behave',
    'pymongo>=4.0.1',
    'auth0-python',
    'cachetools',
    'python-jose',
]

# LOCAL_DEPENDENCIES = [
# ]

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(BASEDIR))

setup(
    name='wf-video-io',
    packages=find_packages(),
    version=VERSION,
    include_package_data=True,
    description='Tools for accessing Wildflower video data',
    long_description=open('README.md').read(),
    url='https://github.com/WildflowerSchools/wf-video-io',
    author='Theodore Quinn',
    author_email='ted.quinn@wildflowerschools.org',
    install_requires=BASE_DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
    # extras_require = {
    #     'test': TEST_DEPENDENCIES,
    #     'local': LOCAL_DEPENDENCIES
    # },
    keywords=['video', 'S3'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
