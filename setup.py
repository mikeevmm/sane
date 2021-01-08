import setuptools

with open("README.md", 'r', encoding="utf-8") as readme_file:
    long_description = readme_file.read()

with open("VERSION", 'r') as version_file:
    VERSION = version_file.read()

setuptools.setup(
        name="sane-build",
        version=VERSION,
        author="Miguel Murça",
        author_email="miguel.murca+pypi@gmail.com",
        description="Make, but Sane",
        long_description=long_description,
        long_description_content_type="text/markdown",
        license="MIT",
        keywords="make makefiles cmd utility cli",
        url="https://github.com/mikeevmm/sane",
        py_modules=["sane"],
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
        ],
        python_requires='>=3.6',
)
