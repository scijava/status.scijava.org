#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# html-report.sh
# ------------------------------------------------------------------------
# Generates an HTML report of the release status of all
# components in the SciJava BOM (org.scijava:pom-scijava).

# -- Constants --

checkMark="&#x2714;"
xMark="&#x2715;"

# -- Functions --

# Gets the maximum of two numbers.
max() {
       test "$1" -gt "$2" && echo "$1" || echo "$2"
}

info() {
  echo $@ 1>&2
}

# -- Main --

# Emit the HTML header matter.
echo '<html>'
echo '<head>'
echo '<title>SciJava software status</title>'
echo '<link type="text/css" rel="stylesheet" href="status.css">'
echo '<link rel="icon" type="image/png" href="favicon.png">'
echo '<script type="text/javascript" src="sorttable.js"></script>'
echo '<script type="text/javascript" src="sortable-badges.js"></script>'
echo '</head>'
echo '<body onload="makeBadgesSortable()">'
echo '<!-- Generated via https://codepo8.github.io/css-fork-on-github-ribbon/ -->'
echo '<span id="forkongithub"><a href="https://github.com/scijava/status.scijava.org">Fix me on GitHub</a></span>'
echo '<table class="sortable">'
echo '<tr>'
echo '<th>groupId</th>'
echo '<th>artifactId</th>'
echo '<th>BOM version</th>'
echo '<th>Newest release</th>'
echo '<th>OK</th>'
echo '<th>Last vetted</th>'
echo '<th>Last updated</th>'
echo '<th>OK</th>'
echo '<th>Action</th>'
echo '<th>Build</th>'
echo '</tr>'

# List components of the BOM, and loop over them.
info "Generating list of components"
./newest-releases.sh | while read line
do
  ga=${line%%,*}
  g=${ga%%:*}
  a=${ga#*:}
  rest=${line#*,}
  bomVersion=${rest%%,*}
  newestRelease=${rest#*,}

  info "Processing $ga"

  # Get project URL
  url=$(./project-url.sh "$g:$a")
  url=${url#* }

  # Compute Travis badge
  case "$url" in
    https://github.com/*)
      slug=${url#https://github.com/}
      travis="<td class=\"badge\"><a href=\"https://travis-ci.org/$slug\"><img src=\"https://travis-ci.org/$slug.svg?branch=master\"></a></td>"
      ;;
    *)
      travis="<td>-</td>"
      ;;
  esac

  # Check BOM version vs. newest release
  if [ "$bomVersion" = "$newestRelease" ]
  then
    bomStatus="bom-ok"
    bomOK=$checkMark
  else
    bomStatus="bom-behind"
    bomOK=$xMark
  fi

  # Discern timestamps for this component.
  timestamps=$(./version-timestamps.sh "$g:$a:$newestRelease")
  timestamps=${timestamps#* }
  releaseTimestamp=${timestamps%% *}
  timestampOverride=$(./timestamp-override.sh "$g:$a")
  lastVetted=$(max "$releaseTimestamp" "$timestampOverride")
  lastUpdated=${timestamps#* }

  # Compute time difference; >24 hours means a new release is needed.
  if [ "$((lastUpdated-lastVetted))" -gt 100000000 ]
  then
    # A SNAPSHOT was deployed more recently than the newest release.
    releaseStatus="release-needed"
    releaseOK=$xMark
  else
    # No SNAPSHOT has happened more than 24 hours after newest release.
    releaseStatus="release-ok"
    releaseOK=$checkMark
  fi

  if [ "$((lastUpdated-lastVetted))" -lt 0 ]
  then
    # NB: Last vetted more recently than last update; no bump needed.
    bomStatus="bom-ok"
    bomOK=$checkMark
  fi

  # Compute action items.
  if [ "$url" -a "$releaseOK" = "$xMark" ]
  then
    action="Cut"
    actionKey=1
  elif [ "$bomOK" = "$xMark" ]
  then
    action="Bump"
    actionKey=2
  else
    action="None"
    actionKey=3
  fi

  # Emit the HTML table row.
  gc=$(echo "$g" | sed 's/[^0-9a-zA-Z]/-/g')
  ac=$(echo "$a" | sed 's/[^0-9a-zA-Z]/-/g')
  echo "<tr class=\"$gc $gc_$ac $bomStatus $releaseStatus\">"
  echo "<td>$g</td>"
  test "$url" &&
    echo "<td><a href=\"$url\">$a</td>" ||
    echo "<td>$a</td>"
  echo "<td>$bomVersion</td>"
  echo "<td>$newestRelease</td>"
  echo "<td>$bomOK</td>"
  if [ "$lastVetted" -eq "$timestampOverride" ]
  then
    # Last vetted manually via timestamps.txt.
    echo "<td class=\"overridden\">$lastVetted</td>"
  elif [ "$timestampOverride" -eq 0 ]
  then
    # Last vetted automatically via release artifact; no timestamp override.
    echo "<td>$lastVetted</td>"
  else
    # Last vetted automatically via release artifact; old timestamp override.
    echo "<td class=\"wasOverridden\">$lastVetted</td>"
  fi
  echo "<td>$lastUpdated</td>"
  echo "<td>$releaseOK</td>"
  echo "<td sorttable_customkey=\"$actionKey\">$action</td>"
  echo "$travis"
  echo '</tr>'
done

# Emit the HTML footer matter.
echo '</table>'
echo '</body>'
echo '</html>'
