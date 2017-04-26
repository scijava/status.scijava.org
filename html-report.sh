#!/bin/sh

# html-report.sh

# Generates an HTML report of the release status of all
# components in the SciJava BOM (org.scijava:pom-scijava).

# -- Constants --

checkMark="&#x2714;"
xMark="&#x2715;"

# -- Functions --

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
echo '</head>'
echo '<body>'
echo '<!-- Generated via https://codepo8.github.io/css-fork-on-github-ribbon/ -->'
echo '<span id="forkongithub"><a href="https://github.com/scijava/status.scijava.org">Fix me on GitHub</a></span>'
echo '<table class="sortable">'
echo '<tr>'
echo '<th>groupId</th>'
echo '<th>artifactId</th>'
echo '<th>BOM version</th>'
echo '<th>Newest release</th>'
echo '<th>OK</th>'
echo '<th>When released</th>'
echo '<th>Last updated</th>'
echo '<th>OK</th>'
echo '<th>Action</th>'
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
  lastUpdated=${timestamps#* }

  # Compute time difference.
  if [ "$((lastUpdated-releaseTimestamp))" -gt 1000000 ]
  then
    # A SNAPSHOT was deployed more recently than the newest release.
    releaseStatus="release-needed"
    releaseOK=$xMark
  else
    # No SNAPSHOT has happened more than 24 hours after newest release.
    releaseStatus="release-ok"
    releaseOK=$checkMark
  fi

  # Compute action items.
  if [ "$url" -a "$bomOK" = "$xMark" ]
  then
    action="Release+Bump"
    actionKey=1
  else if [ "$releaseOK" = "$xMark" ]
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
  echo "<td>$releaseTimestamp</td>"
  echo "<td>$lastUpdated</td>"
  echo "<td>$releaseOK</td>"
  echo "<td sorttable_customkey=\"$actionKey\">$action</td>"
  echo '</td>'
  echo '</tr>'
done

# Emit the HTML footer matter.
echo '</table>'
echo '</body>'
echo '</html>'
