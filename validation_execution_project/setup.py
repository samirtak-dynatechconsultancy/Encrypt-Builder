from setuptools import setup, find_packages
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]


setup(
    name="ge_validation_execution",
    version="0.0.5",
    packages=find_packages(),
    package_data={
        "ge_validation_execution": ["ge_validation_execution_encrypted.enc"]
    },
    include_package_data=True,
    install_requires=requirements,
    description="Encrypted module loader for ge_validation_execution",
    author="Auto Generator",
)
