#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# timestamp-override.sh
# ------------------------------------------------------------------------
# Gets the timestamp when a project was last vetted.
#
# Sometimes, we know a new snapshot has no release-worthy changes since
# the last release. In this scenario, we can record the last time we
# checked a given component in the timestamps.txt file.
#
# This also gives us a hedge against problems with the Maven metadata,
# such as that particular G:A:V not be present in the remote repository
# for any reason (in which case, version-timestamps.sh will emit 0).

processGA() {
	ga=$1
	match=$(grep "^$ga " timestamps.txt | head -n1)
	test "$match" && echo "$match" | sed 's/.* //' || echo 0
}

# ----
# Main
# ----
while test $# -gt 0
do
	processGA "$1"
	shift
done
