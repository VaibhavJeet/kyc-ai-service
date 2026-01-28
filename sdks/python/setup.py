from setuptools import setup, find_packages

setup(
    name="trustvault",
    version="1.0.0",
    description="Official Python SDK for TrustVault API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="TrustVault",
    author_email="sdk@trustvault.io",
    url="https://github.com/trustvault/sdk-python",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="trustvault kyc verification identity face-recognition",
)
