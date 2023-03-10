#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# html-report.py
# ------------------------------------------------------------------------
# Generates an HTML report of the release status of all
# components in the SciJava BOM (org.scijava:pom-scijava).

import datetime, logging, re, subprocess

# -- Constants --

checkMark = "&#x2714;"
xMark = "&#x2715;"
repoBase = "https://maven.scijava.org"
datetime0 = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0)

# -- Data --

def file2map(filepath, sep=' '):
    with open(filepath) as f:
        pairs = [
            line.strip().split(sep, 1)
            for line in f.readlines()
            if not line.strip() == "" and not line.startswith("#")
        ]
    return {pair[0]: pair[1] for pair in pairs}

badge_overrides = file2map('ci-badges.txt')
timestamps = file2map('timestamps.txt')
project_urls = file2map('projects.txt')

group_orgs = {
    'graphics.scenery':   'scenerygraphics',
    'io.scif':            'scifio',
    'net.imagej':         'imagej',
    'net.imglib2':        'imglib',
    'org.openmicroscopy': 'ome',
    'org.scijava':        'scijava',
    'sc.fiji':            'fiji',
    'sc.iview':           'scenerygraphics',
}

# -- Functions --

def newest_releases():
    """
    Dumps the component list for the given BOM (pom-scijava by default).
    The format of each component is groupId:artifactId,bomVersion,newestVersion
    """
    return [token.decode() for token in subprocess.check_output(['./newest-releases.sh']).split()]

def project_url(ga):
    """
    Gets the URL of a project from its G:A.
    """
    if ga in project_urls:
        return project_urls[ga]

    g, a = ga.split(':', 1)

    if g == "sc.fiji":
        if a.startswith('TrackMate'):
            return f'https://github.com/trackmate-sc/{a}'
        elif a.startswith('bigdataviewer'):
            return f'https://github.com/bigdataviewer/{a}'
        elif a.startswith('labkit'):
            return f'https://github.com/juglab/{a}'
        if a.endswith('_'):
            a = a[:-1]

    if g in group_orgs:
        return f'https://github.com/{group_orgs[g]}/{a}'

    return ''

def ts2dt(timestamp):
    """
    Converts timestamp string of the form YYYYMMDDhhmmss to a datetime object.
    """
    if not timestamp: return datetime0
    m = re.match('(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)', timestamp)
    return datetime.datetime(*map(int, m.groups())) if m else datetime0

def version_timestamps(g, a, v):
    """
    Gets timestamps for the last time a component was released.
    Returns a (releaseTimestamp, lastDeployed) pair.
    """
    gav, releaseTimestamp, lastDeployed = subprocess.check_output(['./version-timestamps.sh', f'{g}:{a}:{v}']).decode().strip('\n\r').split(' ')
    assert gav == f'{g}:{a}:{v}'
    return ts2dt(releaseTimestamp), ts2dt(lastDeployed)

def badge(url):
    slug = None
    if url.startswith('https://github.com/'):
        slug = url[len('https://github.com/'):]
    if slug in badge_overrides:
        return badge_overrides[slug]
    if slug:
        return f"<td class=\"badge\"><a href=\"https://github.com/{slug}/actions\"><img src=\"https://github.com/{slug}/actions/workflows/build-main.yml/badge.svg\"></a></td>"
    return "<td>-</td>"

def timestamp_override(g, a):
    """
    Gets the timestamp when a project was last vetted.

    Sometimes, we know a new snapshot has no release-worthy changes since
    the last release. In this scenario, we can record the last time we
    checked a given component in the timestamps.txt file.

    This also gives us a hedge against problems with the Maven metadata,
    such as that particular G:A:V not be present in the remote repository
    for any reason (in which case, this function returns 0).
    """
    return ts2dt(timestamps.get(f'{g}:{a}', None))

def release_link(g, a, v):
    return f"<a href=\"{repoBase}/#nexus-search;gav~{g}~{a}~{v}~~\">{v}</a>"

# -- Main --

# Emit the HTML header matter.
print('<html>')
print('<head>')
print('<title>SciJava software status</title>')
print('<link type="text/css" rel="stylesheet" href="status.css">')
print('<link rel="icon" type="image/png" href="favicon.png">')
print('<script type="text/javascript" src="sorttable.js"></script>')
print('<script type="text/javascript" src="sortable-badges.js"></script>')
print('</head>')
print('<body onload="makeBadgesSortable()">')
print('<!-- Generated via https://codepo8.github.io/css-fork-on-github-ribbon/ -->')
print('<span id="forkongithub"><a href="https://github.com/scijava/status.scijava.org">Fix me on GitHub</a></span>')
print('<table class="sortable">')
print('<tr>')
print('<th>Artifact</th>')
print('<th>Release</th>')
print('<th>OK</th>')
print('<th>Last vetted</th>')
print('<th>Last updated</th>')
print('<th>OK</th>')
print('<th>Action</th>')
print('<th>Build</th>')
print('</tr>')

# List components of the BOM, and loop over them.
logging.info("Generating list of components")
for line in newest_releases():
    ga, bomVersion, newestRelease = line.split(',')
    g, a = ga.split(':')

    logging.info(f"Processing {ga}")

    # Get project metadata
    url = project_url(ga)
    ciBadge = badge(url)

    # Check BOM version vs. newest release
    if bomVersion == newestRelease:
        bomStatus = "bom-ok"
        bomOK = checkMark
    else:
        bomStatus = "bom-behind"
        bomOK = xMark

    # Discern timestamps for this component.
    #
    # Each component is "vetted" either by:
    #   A) being released; or
    #   B) adding an override to timestamps.txt.
    # Our goal here is to detect whether the component has changed since
    # the most recent release (not the release listed in the BOM).
    releaseTimestamp, lastUpdated = version_timestamps(g, a, newestRelease)
    timestampOverride = timestamp_override(g, a)
    lastVetted = max(releaseTimestamp, timestampOverride)

    # Compute time difference; >24 hours means a new release is needed.
    if lastUpdated - lastVetted > datetime.timedelta(days=1):
        # A SNAPSHOT was deployed more recently than the newest release.
        releaseStatus = "release-needed"
        releaseOK = xMark
    else:
        # No SNAPSHOT has happened more than 24 hours after newest release.
        releaseStatus = "release-ok"
        releaseOK = checkMark

    if lastUpdated < timestampOverride:
        # NB: Manually vetted more recently than last update; no bump needed.
        bomStatus = "bom-ok"
        bomOK = checkMark

    # Compute action items.
    if url and releaseOK == xMark:
        action = "Cut"
        actionKey = 1
    elif bomOK == xMark:
        action = "Bump"
        actionKey = 2
    else:
        action = "None"
        actionKey = 3

    # Emit the HTML table row.
    gc = re.sub('[^0-9A-Za-z]', '-', g)
    ac = re.sub('[^0-9A-Za-z]', '-', a)
    print(f"<tr class=\"g-{gc} a-{ac} {bomStatus} {releaseStatus}\">")
    if url:
        print(f"<td><a href=\"{url}\">{g} : {a}</td>")
    else:
        print(f"<td>{g} : {a}</td>")

    if bomVersion == newestRelease:
        print(f"<td>{release_link(g, a, newestRelease)}</td>")
    else:
        print(f"<td>{release_link(g, a, bomVersion)} &rarr; {release_link(g, a, newestRelease)}</td>")

    print(f"<td>{bomOK}</td>")
    if lastVetted == 0:
        # Unknown status!
        print("<td class=\"unknown\">???</td>")
    elif lastVetted == timestampOverride:
        # Last vetted manually via timestamps.txt.
        print(f"<td class=\"overridden\">{lastVetted}</td>")
    elif timestampOverride == datetime0:
        # Last vetted automatically via release artifact; no timestamp override.
        print(f"<td>{lastVetted}</td>")
    else:
        # Last vetted automatically via release artifact; old timestamp override.
        print(f"<td class=\"wasOverridden\">{lastVetted}</td>")
    print(f"<td>{lastUpdated}</td>")
    print(f"<td>{releaseOK}</td>")
    print(f"<td sorttable_customkey=\"{actionKey}\">{action}</td>")
    print(ciBadge)
    print('</tr>')

# Emit the HTML footer matter.
print('</table>')
with open('footer.html') as f:
    print(f.read().strip())
print('</body>')
print('</html>')
