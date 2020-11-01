from setuptools import setup, find_packages

setup(
    name='digsigserver',
    version='0.3.4',
    packages=find_packages(),
    license='MIT',
    author='Matt Madison',
    author_email='matt@madison.systems',
    entry_points={
        'console_scripts': [
            'digsigserver = digsigserver.scripts.digsigserver:main',
        ]
    },
    install_requires=['sanic']
)
