from setuptools import setup

setup(
    name="canvas-nbgrader",
    version="0.0.3",
    author="Olav Vahtras",
    author_email="vahtras@kth.se",
    py_modules=["cnb", "util"],
    install_requires=["pandas", "canvasapi"],
    entry_points={
        'console_scripts': ['cnb=cnb:main']
        },
)
