#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# newest-releases.sh
# ------------------------------------------------------------------------
# Dumps the component list for the given BOM (pom-scijava by default).
# The format of each component is groupId:artifactId,bomVersion,newestVersion

dir=$(cd "$(dirname "$0")" && pwd)

test "$1" &&
  pomURL=$1 ||
  pomURL=https://raw.githubusercontent.com/scijava/pom-scijava/master/pom.xml

pomFile=$(mktemp -t status.scijava.org-XXXX)
curl -fs "$pomURL" > "$pomFile"

mvn -B -U -Dverbose=true -f "$pomFile" -s settings.xml \
  -Dmaven.version.rules=file://$dir/rules.xml \
  versions:display-dependency-updates |
  # Standardize the output format for too-long G:A strings.
  perl -0777 -pe 's/\.\.\.\n\[INFO\] */ ... /igs' |
  # Filter to only the relevant lines.
  grep '[^ ]*:[^ ]* \.\.\.\.* ' |
  # Strip the [INFO] prefix.
  sed 's/^\[INFO\] *//' |
  # Catch when there is a version update.
  sed 's/ *\.\.\.\.* *\([^ ]*\) *-> *\([^ ]*\)/,\1,\2/' |
  # Catch when there is no version update.
  sed 's/ *\.\.\.\.* *\([^ ]*\) */,\1,\1/' |
  # Sort the results.
  sort

rm "$pomFile"
