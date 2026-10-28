from setuptools import find_packages, setup

setup(
    name="appli_web_budget",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.0.0",
        "Flask-SQLAlchemy>=2.5.0",
        "Flask-Migrate>=3.0.0",
        "Flask-Mail>=0.9.1",
        "Flask-Babel>=3.0.0",
        "Flask-WTF>=1.0.0",
        "Flask-CORS>=3.0.0",
        "Flask-JWT-Extended>=4.0.0",
        "Flask-Limiter>=2.0.0",
        "Flask-Caching>=2.0.0",
        "Flask-Restx>=1.0.0",
        "email-validator>=1.1.3",
        "python-dotenv>=0.19.0",
        "SQLAlchemy>=1.4.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-flask>=1.2.0",
            "pytest-mock>=3.10.0",
            "coverage>=6.0.0",
            "factory-boy>=3.2.0",
            "Faker>=13.0.0",
        ],
    },
)
