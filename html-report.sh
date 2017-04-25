#!/bin/sh

# generate-html-report.sh

# Generates an HTML report of the release status of all
# components in the SciJava BOM (org.scijava:pom-scijava).

# Emit the HTML header matter.
echo '<html>'
echo '<head>'
echo '<title>SciJava software status</title>'
echo '<link type="text/css" rel="stylesheet" href="status.css">'
echo '<link rel="icon" type="image/png" href="favicon.png">'
echo '<script type="text/javascript" src="sorttable.js">'
echo '</head>'
echo '<body>'
echo '<table>'
echo '<tr>'
echo '<th>Status</th>'
echo '<th>groupId</th>'
echo '<th>artifactId</th>'
echo '<th>BOM version</th>'
echo '<th>Newest release</th>'
echo '<th>When released</th>'
echo '<th>Last updated</th>'
echo '</tr>'

# List components of the BOM, and loop over them.
./newest-releases.sh | while read line
do
  ga=${line%%,*}
  g=${ga%%:*}
  a=${ga#*:}
  rest=${line#*,}
  bomVersion=${rest%%,*}
  newestRelease=${rest#*,}

  # Discern timestamps for this component.
  timestamps=$(./version-timestamps.sh "$g:$a:$newestRelease")
  timestamps=${timestamps#* }
  releaseTimestamp=${timestamps%% *}
  lastUpdated=${timestamps#* }

  # Compute time difference.
  let age="$lastUpdated-$releaseTimestamp"
  if [ "$age" -gt 3000 ]
  then
    status="behind"
    symbol="&#x2715;" # X mark
  else
    status="released"
    symbol="&#x2714;" # check mark
  fi

  # Emit the HTML table row.
  gc=$(echo "$g" | sed 's/[^0-9a-zA-Z_]/_/g')
  ac=$(echo "$a" | sed 's/[^0-9a-zA-Z_]/_/g')
  echo "<tr class=\"$gc $gc_$ac $status\">"
  echo "<td>$symbol</td>"
  echo "<td>$g</td>"
  echo "<td>$a</td>"
  echo "<td>$bomVersion</td>"
  echo "<td>$newestRelease</td>"
  echo "<td>$releaseTimestamp</td>"
  echo "<td>$lastUpdated</td>"
  echo '</td>'
  echo '</tr>'
done

# Emit the HTML footer matter.
echo '</table>'
echo '</body>'
echo '</html>'
