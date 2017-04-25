#!/bin/sh

# newest-releases.sh

# Dumps the component list for the given BOM (pom-scijava by default).
# The format of each component is groupId:artifactId,bomVersion,newestVersion

test "$1" &&
  pomURL=$1 ||
  pomURL=https://raw.githubusercontent.com/scijava/pom-scijava/master/pom.xml

pomFile=$(mktemp -t status.scijava.org)
curl -fs "$pomURL" > "$pomFile"

cat tmp.txt |
#mvn -U -Dverbose=true -f "$pomFile" -s settings.xml \
#  versions:display-dependency-updates |
  # Standardize the output format for too-long G:A strings.
  perl -0777 -pe 's/\.\.\.\n\[INFO\] */ ... /igs' |
  # Filter to only the relevant lines.
  grep ' \.\.\.\.* ' |
  # Strip the [INFO] prefix.
  sed 's/^\[INFO\] *//' |
  # Catch when there is a version update.
  sed 's/ *\.\.\.\.* *\([^ ]*\) *-> *\([^ ]*\)/,\1,\2/' |
  # Catch when there is no version update.
  sed 's/ *\.\.\.\.* *\([^ ]*\) */,\1,\1/' |
  # Sort the results.
  sort

rm "$pomFile"
