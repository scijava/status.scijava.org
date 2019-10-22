#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# version-timestamps.sh
# ------------------------------------------------------------------------
# Gets timestamps for the last time a component was released.
#
# For each G:A:V argument passed to the script,
# there is one line of output, formatted as follows:
#
#     G:A:V releaseTimestamp lastDeployed

# --------------------------------------------------------------
# Set the M2_REPO_PATH variable to the desired Maven repository.
# This can be a remote repository, or a local file path.
# --------------------------------------------------------------
test "$M2_REPO_PATH" && repo=$M2_REPO_PATH ||
	repo=https://maven.scijava.org/content/groups/public

# G=groupId, A=artifactId, V=version
processGAV() {
	debug processGAV $@
	g=$1; a=$2; v=$3
	releaseTimestamp=$(releaseTimestamp "$g" "$a" "$v")
	newestSnapshot=$(newestSnapshot "$g" "$a")
	lastDeployed=$(snapshotTimestamp "$g" "$a" "$newestSnapshot")
	echo "$g:$a:$v $releaseTimestamp $lastDeployed"
}

# Given a release GAV, discerns when it was deployed.
releaseTimestamp() {
	debug releaseTimestamp $@
	g=$1; a=$2; v=$3
	case "$repo" in
		/*) # LOCAL
			# Obtain timestamp from the local file system.
			# Much faster than doing a remote call via cURL.
			for f in "$repo"/*/"$(gpath "$g")/$a/$v/$a-$v.pom"
			do
				test -f "$f" &&
					# NB: We assume GNU stat here, for now!
					formatTimestamp "$(stat -c %y "$f")" ||
					# No file; probably no such release.
					echo 0
			done | sort | tail -n1
			;;
		*) # REMOTE
			# Query the POM's HTTP header for the last modified time.
			url="$repo/$(gpath "$g")/$a/$v/$a-$v.pom"
			debug "releaseTimestamp: url -> $url"
			modified=$(curl -Ifs "$url" | grep '^Last-Modified' | sed 's/^[^ ]* //')
			debug "releaseTimestamp: modified -> $modified"
			test "$modified" &&
				formatTimestamp "$modified" ||
				# Invalid URL; probably no such release.
				echo 0
			;;
	esac
}

# Given a GA, discerns the newest snapshot version.
newestSnapshot() {
	debug newestSnapshot $@
	# Extract <versioning><latest> value.
	extractTag latest $@
}

# Given a GAV, discerns when that snapshot was last deployed.
snapshotTimestamp() {
	debug snapshotTimestamp $@
	g=$1; a=$2; v=$3
	# Extract <versioning><snapshot><timestamp> value.
	extractTag timestamp "$g" "$a/$v" | tr -d '.'
}

# Given a GA(V), extracts an XML tag from local or remote maven-metadata.xml.
extractTag() {
	debug extractTag $@
	tag=$1; g=$2; av=$3
	case "$repo" in
		/*) # LOCAL
			# Extract tag value from each maven-metadata.xml.
			# Then sort and take the last entry as newest.
			for f in "$repo"/*/"$(gpath "$g")/$av/maven-metadata.xml"
			do
				cat "$f" | tagValue "$tag"
			done | sort | tail -n1
			;;
		*) # REMOTE
			# Extract versioning/latest from the remote metadata.
			metadata=$(downloadMetadata "$g" "$av")
			tagValue=$(echo "$metadata" | tagValue "$tag")
			debug "newestSnapshot: $tag -> $tagValue"
			test "$tagValue" || die 1 "No $tag tag in metadata:\n$metadata"
			echo "$tagValue"
			;;
	esac
}

# Downloads maven-metadata.xml from the remote repository as needed.
downloadMetadata() {
	debug downloadMetadata $@
	g=$1; av=$2
	url="$repo/$(gpath "$g")/$av/maven-metadata.xml"
	test "$cachedMetadata" || cachedMetadata=$(curl -fs "$url")
	test "$cachedMetadata" || die 2 "Cannot access metadata remotely from: $url"
	debug "downloadMetadata: cachedMetadata ->\n$cachedMetadata"
	echo "$cachedMetadata"
}

# Clears the contents of downloaded maven-metadata.xml.
clearMetadataCache() {
	debug clearMetadataCache $@
	unset cachedMetadata
}

# Converts dot-separated groupId into slash-separated form.
gpath() {
	debug gpath $@
	echo "$1" | tr '.' '/'
}

# Converts a timestamp to YYYYmmddHHMMSS format.
formatTimestamp() {
	debug formatTimestamp $@
	# Grr, BSD date vs. GNU date!
	# On macOS, you must `brew install coreutils`.
	which gdate >/dev/null &&
		gdate -d "$1" +%Y%m%d%H%M%S ||
		date -d "$1" +%Y%m%d%H%M%S
}

# Extract the CDATA of the given element.
tagValue() {
	# NB: I would love to use xmllint --xpath for this, but it
	# segfaulted in some of my tests. So we go low tech instead.
	debug tagValue $@
	grep "<$1>" | sed "s_.*<$1>\(.*\)</$1>.*_\1_"
}

# Exits the script with an error code + message.
die() {
	debug die $@
	echo "$2" 1>&2
	exit $1
}

debug() {
	test "$DEBUG" && echo "[DEBUG] $@" 1>&2
}

# ----
# Main
# ----
while test $# -gt 0
do
	clearMetadataCache
	case "$1" in
		*:*:*)
			gav=$1
			g=${gav%%:*}
			rest=${gav#*:}
			a=${rest%%:*}
			v=${rest#*:}
			processGAV "$g" "$a" "$v"
			;;
		*)
			echo "[WARNING] Ignoring invalid argument: $1" 2>&1
			;;
	esac
	shift
done
