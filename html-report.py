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

import datetime, logging, pathlib, re, subprocess, sys

from github_issues import GitHubIssues

# -- Constants --

checkMark = "&#x2714;"
xMark = "&#x2715;"
questionMark = "&#10067;" # 10068, 9072
bangMark = "&#10071;" # 10069
warningSign = "&#9888;"

repoBase = "https://maven.scijava.org"
datetime0 = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0)
cacheDir = pathlib.Path('.cache')

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
group_orgs = file2map('group-orgs.txt')

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

issues = GitHubIssues()
cached_issues = cacheDir / 'issues.json'
if cached_issues.is_file():
    issues.load(cached_issues)
    print(f'Got {len(issues.issues())} issues from local cache')
else:
    # HACK: Hardcode the five core orgs for now.
    # CTR TODO: Make this extensible. The artifacts with issueManagement of
    # https://github.com/<org>/<repo>/issues are the ones we want to fetch.
    # Consider doing $(mvn dependency:get ...) if we don't already have the
    # info locally, then we can freely utilize local pom.xml files and
    # maven-metadata-local.xml.
    query = 'user:scijava+user:imglib+user:imagej+user:scifio+user:fiji'
    issues.download(query)
    if cacheDir.is_dir():
        issues.save(cached_issues)
    print(f'Got {len(issues.issues())} issues from GitHub')

sys.exit(0)

# === Information gathering ===

logging.info("Generating list of components")
newest_release_list = newest_releases()

# Process each component on the list.
for line in newest_release_list:
    ga, bomVersion, newestRelease = line.split(',')
    g, a = ga.split(':')

    logging.info(f"Processing {ga}")

    # Get project metadata
    url = project_url(ga)
    ciBadge = badge(url)

lines = [token.decode() for token in subprocess.check_output(['./newest-releases.sh']).split()]
releases = newest_releases()

"""
........

generate-mega-melt.py in pom-scijava/tests is close to what we need.
Want to generate a minimal POM depending on everything in pom-scijava depMgmt.
Then 'mvn -B -U -Denforcer.skip dependency:list', which will resolve (download!) all POMs (but not JARs).
  -- except THIS IS WRONG -- in my tests, JARs are downloaded too. :-(
  -- need to find a way, with one mvn invocation, to download only all the POMs, but not the JARs.
  -- maybe adding <type>pom</type> to each dependency would work, followed by dependency:resolve?

Some components might be at non-existent versions, and fail the dependency:list command, but that doesn't matter.
We'll be able to tell that those versions don't exist when we look in the ~/.m2/repository.

Is there a way to merge status.scijava.org table generation into pom-scijava repo?
There is substantial overlap between mega-melt testing and table generation.
Maybe status.scijava.org could become only the web page, without any GitHub Action.
And then in pom-scijava, we'd have:
    - daily action to regenerate the table
    - push to main action to run mega-melt THEN regenerate the table
        - that same action, if release.properties is there, does release instead
    - PR action to run mega-melt only

Anyway, the workflow for this script becomes:

1. 

........
"""

#logging.info("Downloading GitHub issues")
# HACK: Hardcode the five core orgs for now.
# CTR TODO: Make this extensible. The artifacts with issueManagement of
# https://github.com/<org>/<repo>/issues are the ones we want to fetch.
# Consider doing $(mvn dependency:get ...) if we don't already have the
# info locally, then we can freely utilize local pom.xml files and
# maven-metadata-local.xml.
#query = 'user:scijava+user:imglib+user:imagej+user:scifio+user:fiji';
#issues = download_issues(query)

# === Table output ===

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
for line in releases:
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

    # Changes since vetted (replace space with T):
    # - https://github.com/scijava/scijava-common/commits/master?since=2021-09-09T10:05:24
    # Changes since release:
    # - https://github.com/scijava/scijava-common/compare/scijava-common-2.87.0...master
    # need to know which branch is HEAD (main/master/etc)
    # Should we mark stale timestamp overrides at all? They don't hurt anything; red highlight is annoying.
    #
    # How many open issues are there? How many open PRs?
    # - curl -fs https://api.github.com/search/issues?q=user:$org+type:pr+is:open&sort=created&order=asc&page=$p > $org-$p.json
    # https://stackoverflow.com/a/50731243/1207769


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
