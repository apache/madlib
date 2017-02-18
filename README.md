![](https://github.com/apache/incubator-madlib/blob/master/doc/imgs/magnetic-icon.png) ![](https://github.com/apache/incubator-madlib/blob/master/doc/imgs/agile-icon.png) ![](https://github.com/apache/incubator-madlib/blob/master/doc/imgs/deep-icon.png)
=================================================
**MADlib<sup>&reg;</sup>** is an open-source library for scalable in-database analytics.
It provides data-parallel implementations of mathematical, statistical and
machine learning methods for structured and unstructured data.

Installation and Contribution
==============================
See the project webpage  [`MADlib Home`](http://madlib.incubator.apache.org/) for links to the
latest binary and source packages. For installation and contribution guides,
please see [`MADlib Wiki`](https://cwiki.apache.org/confluence/display/MADLIB/)

Development with Docker
=======================
We provide a docker image with necessary dependencies required to compile and test MADlib. You can
view the dependency docker file at `./src/tool/docker/base/Dockerfile_postgres_9_6`. The image is
hosted on docker hub at `madlib/postgres_9.6:latest`. This docker image is currently under heavy
development.

Some useful commands to use the docker file:
```
# Build the image from the docker file:
docker build -t madlib -f tool/docker/postgres/Dockerfile_9_6 .

# Run the container, mounting the source code's folder to the container:
docker run -d -it --name madlib -v (path-to-incubator-madlib)/src:/incubator-madlib/src madlib

# When the container is up, connect to it and install MADlib:
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install

# Run install-check on the source code:
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install-check

## To change code, build and run install check on the changed code:
# Go into the container to run various build related commands:
docker exec -it madlib bash
cd /incubator-madlib/build

# Compile MADlib after changing code in your source repo (note that code changes made in your source folder
# will be reflected in the container too, since we mounted the volume when docker run was performed).
make

# Run install check on a specific module, say svm:
src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres install-check -t svm

# Install or reinstall MADlib if required:
src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres install
src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres reinstall
```

User and Developer Documentation
==================================
The latest documentation of MADlib modules can be found at [`MADlib
Docs`](http://madlib.incubator.apache.org/docs/latest/index.html).


Architecture
=============
The following block-diagram gives a high-level overview of MADlib's
architecture.


![MADlib Architecture](https://github.com/apache/incubator-madlib/blob/master/doc/imgs/architecture.png)


Third Party Components
======================
MADlib incorporates material from the following third-party components

1. [`argparse 1.2.1`](http://code.google.com/p/argparse/) "provides an easy, declarative interface for creating command line tools"
2. [`Boost 1.47.0 (or newer)`](http://www.boost.org/) "provides peer-reviewed portable C++ source libraries"
3. [`Eigen 3.2.2`](http://eigen.tuxfamily.org/index.php?title=Main_Page) "is a C++ template library for linear algebra"
4. [`PyYAML 3.10`](http://pyyaml.org/wiki/PyYAML) "is a YAML parser and emitter for Python"
5. [`PyXB 1.2.4`](http://pyxb.sourceforge.net/) "is a Python library for XML Schema Bindings"

Licensing
==========
License information regarding MADlib and included third-party libraries can be
found inside the [`license`](https://github.com/apache/incubator-madlib/blob/master/licenses) directory.

Release Notes
=============
Changes between MADlib versions are described in the
[`ReleaseNotes.txt`](https://github.com/apache/incubator-madlib/blob/master/RELEASE_NOTES) file.

Papers and Talks
=================
* [`MAD Skills : New Analysis Practices for Big Data (VLDB 2009)`](http://db.cs.berkeley.edu/papers/vldb09-madskills.pdf)
* [`Hybrid In-Database Inference for Declarative Information Extraction (SIGMOD 2011)`](https://amplab.cs.berkeley.edu/publication/hybrid-in-database-inference-for-declarative-information-extraction/)
* [`Towards a Unified Architecture for In-Database Analytics (SIGMOD 2012)`](http://www.cs.stanford.edu/~chrismre/papers/bismarck-full.pdf)
* [`The MADlib Analytics Library or MAD Skills, the SQL (VLDB 2012)`](http://www.eecs.berkeley.edu/Pubs/TechRpts/2012/EECS-2012-38.html)


Related Software
=================
* [`PivotalR`](https://github.com/pivotalsoftware/PivotalR) - PivotalR also
lets the user run the functions of the open-source big-data machine learning
package `MADlib` directly from R.
* [`PyMADlib`](https://github.com/pivotalsoftware/pymadlib) - PyMADlib is a python
wrapper for MADlib, which brings you the power and flexibility of python
with the number crunching power of `MADlib`.
