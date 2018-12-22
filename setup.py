from setuptools import setup

def readme():
  with open("README.md") as f:
    return f.read()

setup(
  name = "yOpenApi",
  version = "0.0.1",
  description = "OpenApi for yModel and ySanic",
  long_description = readme(),
  classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Plugins",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "Programming Language :: Python :: 3",
    "Topic :: Database"
  ],
  keywords = "openapi marshmallow ySanic",
  url = "https://github.com/Garito/yOpenApi",
  author = "Garito",
  author_email = "garito@gmail.com",
  license = "GPLv3+",
  packages = ["yOpenApi"],
  install_requires = [
    "yModel",
    "ySanic"
  ],
  test_suite = "unittest"
)
