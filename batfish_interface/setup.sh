#!/bin/bash

GITHUBPATH=$1
REPONAME=$2
C2SPATH=$3

# copy files over
rsync -r -P --include=*/ --include=*.java --include=pom.xml --include=MANIFEST.MF --exclude=* "$C2SPATH/batfish_interface/" "$GITHUBPATH/$REPONAME/projects/"