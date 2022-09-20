import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="whirlpool_sixth_sense",
    version="0.18.0",
    author="Abílio Costa",
    author_email="amfcalt@gmail.com",
    description="Unofficial API for Whirlpool's 6th Sense appliances",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abmantis/whirlpool-sixth-sense/",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=install_requires,
)
