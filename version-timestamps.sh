#!/bin/sh

# version-timestamps.sh
#
# Gets timestamps for the last time a component was released.
#
# For each G:A:V argument passed to the script,
# there is one line of output, formatted as follows:
#
#     G:A:V releaseTimestamp lastUpdated

# --------------------------------------------------------------
# Set the M2_REPO_PATH variable to the desired Maven repository.
# This can be a remote repository, or a local file path.
# --------------------------------------------------------------
test "$M2_REPO_PATH" && repo=$M2_REPO_PATH ||
	repo=https://maven.imagej.net/content/groups/public

# G=groupId, A=artifactId, V=version
processGAV() {
	debug processGAV $@
	g=$1; a=$2; v=$3
	versionTimestamp=$(versionTimestamp "$g" "$a" "$v")
	lastUpdated=$(lastUpdated "$g" "$a" "$v")
	echo "$g:$a:$v $versionTimestamp $lastUpdated"
}

# Given a GAV, discerns when it was deployed.
versionTimestamp() {
	debug versionTimestamp $@
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
			debug "versionTimestamp: url -> $url"
			modified=$(curl -Ifs "$url" | grep '^Last-Modified' | sed 's/^[^ ]* //')
			debug "versionTimestamp: modified -> $modified"
			test "$modified" &&
				formatTimestamp "$modified" ||
				# Invalid URL; probably no such release.
				echo 0
			;;
	esac
}

# Given a GA, discerns when the latest version was deployed.
# This is probably, but not necessarily, the timestamp
# corresponding to the most recently deployed SNAPSHOT.
lastUpdated() {
	debug lastUpdated $@
	g=$1; a=$2
	case "$repo" in
		/*) # LOCAL
			# Extract versioning/lastUpdated from each maven-metadata.xml.
			# Then sort and take the last entry as newest.
			for f in "$repo"/*/"$(gpath "$g")/$a/maven-metadata.xml"
			do
				cat "$f" | tagValue lastUpdated
			done | sort | tail -n1
			;;
		*) # REMOTE
			# Extract versioning/lastUpdated from the remote metadata.
			metadata=$(downloadMetadata "$g" "$a")
			lastUpdated=$(echo "$metadata" | tagValue lastUpdated)
			debug "lastUpdated: lastUpdated -> $lastUpdated"
			test "$lastUpdated" || die 1 "No lastUpdated tag in metadata:\n$metadata"
			echo "$lastUpdated"
			;;
	esac
}

# Downloads maven-metadata.xml from the remote repository as needed.
downloadMetadata() {
	debug downloadMetadata $@
	g=$1; a=$2
	url="$repo/$(gpath "$g")/$a/maven-metadata.xml"
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
