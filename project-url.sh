#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# project-url.sh
# ------------------------------------------------------------------------
# Gets the URL of a project from its G:A.

# G=groupId, A=artifactId
processGA() {
	ga=$1
	match=$(grep "^$ga " projects.txt)
	if [ "$match" ]
	then
		echo "$match"
	else
		g=${ga%%:*}
		a=${ga#*:}
		test "$g" = "graphics.scenery" && url=https://github.com/scenerygraphics/$a
		test "$g" = "io.scif" && url=https://github.com/scifio/$a
		test "$g" = "net.imagej" && url=https://github.com/imagej/$a
		test "$g" = "net.imglib2" && url=https://github.com/imglib/$a
		test "$g" = "org.scijava" && url=https://github.com/scijava/$a
		if [ "$g" = "sc.fiji" ]
		then
			case "$a" in
				bigdataviewer*)
					url=https://github.com/bigdataviewer/$a
					;;
				*)
					url=https://github.com/fiji/${a%_}
					;;
			esac
		fi
		test "$g" = "sc.iview" && url=https://github.com/scenerygraphics/$a
		test -z "$url" && exit 1 # no known URL
		echo "$ga $url"
	fi
}

# ----
# Main
# ----
while test $# -gt 0
do
	processGA "$1"
	shift
done
