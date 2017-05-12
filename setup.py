from setuptools import find_packages, setup

tests_requirements = [
    'pytest',
    'pytest-cov',
    'pytest-flake8',
    'pytest-isort',
]

setup(
    name="wall-it",
    version="0.1.dev0",
    description="Wall It",
    url="https://wall-it.kozea.fr",
    author="Kozea",
    packages=find_packages(),
    include_package_data=True,
    scripts=['wallit.py'],
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'httplib2',
        'oauth2client',
        'Pygal',
        'WeasyPrint',
    ],
    tests_requires=tests_requirements,
    extras_require={'test': tests_requirements}
)
