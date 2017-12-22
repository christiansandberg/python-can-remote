from setuptools import setup, find_packages

exec(open("can_remote/version.py").read())

description = open("README.rst").read()

setup(
    name="python-can-remote",
    url="https://github.com/christiansandberg/python-can-remote",
    version=__version__,
    packages=find_packages(),
    author="Christian Sandberg",
    author_email="christiansandberg@me.com",
    description="CAN over network bridge for Python",
    keywords="CAN TCP websocket",
    long_description=description,
    license="MIT",
    platforms=["any"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering"
    ],
    package_data={
        "can_remote": ["web/index.html", "web/assets/*"]
    },
    install_requires=["python-can>=2.0.0rc1"]
)
