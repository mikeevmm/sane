import setuptools

with open("README.md", 'r', encoding="utf-8") as readme_file:
    long_description = readme_file.read()

setuptools.setup(
        name="sane-miguelmurca",
        version="2.0",
        author="Miguel Murça",
        author_email="miguel.murca+pypi@gmail.com",
        description="Make, but Sane",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/mikeevmm/sane",
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
        ],
        python_requires='>=3.6',
)
