from setuptools import setup

setup(
    name="cnb",
    version="0.0.1",
    author="Olav Vahtras",
    author_email="vahtras@kth.se",
    py_modules=["cnb"],
    install_requires=["pandas", "canvasapi"],
    entry_points={
        'console_scripts': ['cnb=cnb:main']
        },
)
