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
## 1) Pull down the `madlib/postgres_9.6:latest` image from docker hub:
docker pull madlib/postgres_9.6:latest

############################################## * WARNING * ##############################################
# Beware of mounting a volume as shown below. Changes you make in the "incubator-madlib" folder inside the
# docker container will be reflected on your disk (and vice versa). Accidental deletion of data in the
# mounted volume from a docker container will result in deletion of the data in your local disk as well.
#########################################################################################################
## 2) Launch a container corresponding to the MADlib image, mounting the source code's folder to the container.
docker run -d -it --name madlib -v (path-to-incubator-madlib-source-code):/incubator-madlib/ madlib/postgres_9.6

## 3) When the container is up, connect to it and build MADlib:
mkdir /incubator-madlib/build-docker
cd /incubator-madlib/build-docker
cmake ..
make
make doc
make install

## 4) Install MADlib:
src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install

## 5) Several other commands, apart from the ones above can now be run, such as:
# Run install check, on all modules:
src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install-check
# Run install check, on a specific module, say svm:
src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install-check -t svm
# Reinstall MADlib:
src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres reinstall

## 6) Kill and remove containers (after exiting the container):
docker kill madlib
docker rm madlib
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
