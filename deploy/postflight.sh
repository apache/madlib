#!/bin/bash

# $0 - Script Path, $1 - Package Path, $2 - Target Location, and $3 - Target Volume

MADLIB_VERSION=2.1.0

# Remove existing soft links
find $2/usr/local/madlib/bin -depth -type l -exec rm {} \; 2>/dev/null
find $2/usr/local/madlib/doc -depth -type l -exec rm {} \; 2>/dev/null
find $2/usr/local/madlib/Current -depth -type l -exec rm {} \; 2>/dev/null

# Create new soft links
ln -nsf $2/usr/local/madlib/Versions/$MADLIB_VERSION $2/usr/local/madlib/Current
ln -nsf $2/usr/local/madlib/Current/bin $2/usr/local/madlib/bin
ln -nsf $2/usr/local/madlib/Current/doc $2/usr/local/madlib/doc

if [ -d "$2/usr/local/madlib/Versions.bak" ];
then
    mv -f $2/usr/local/madlib/Versions.bak/* $2/usr/local/madlib/Versions/
    rm -rf $2/usr/local/madlib/Versions.bak
fi
