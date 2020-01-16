from setuptools import setup, find_packages

setup(
    name='digsigserver',
    version='0.0.0',
    packages=find_packages(),
    license='MIT',
    author='Matt Madison',
    author_email='matt@madison.systems',
    install_requires=['sanic']
)
