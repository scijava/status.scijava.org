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

cacheFile=
test -d .cache &&
  cacheFile=.cache/newest-releases &&
  test -f "$cacheFile" && cat "$cacheFile" && exit 0

test "$1" &&
  pomURL=$1 ||
  pomURL=https://raw.githubusercontent.com/scijava/pom-scijava/master/pom.xml

pomFile=$(mktemp -t status.scijava.org-XXXX)
curl -fs "$pomURL" > "$pomFile"

result=$(mvn -B -U -Dverbose=true -f "$pomFile" -s settings.xml \
  -Dmaven.version.rules=https://raw.githubusercontent.com/scijava/pom-scijava/master/rules.xml \
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
  sort -u)

  echo "$result" | tee $cacheFile

rm "$pomFile"
