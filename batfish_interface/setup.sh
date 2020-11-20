#!/bin/bash

REPOPATH=$1
C2SPATH=$2

# copy files over
rsync -r -P --include=*/ --include=*.java --include=pom.xml --include=MANIFEST.MF --exclude=* "$C2SPATH/batfish_interface/" "$REPOPATH/projects/"
