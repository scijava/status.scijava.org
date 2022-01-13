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

import datetime, json, logging, pathlib, re, subprocess, sys

# TEMP: regex: what is \b ?
#
from maven import ts2dt

# -- Constants --

checkMark = "&#x2714;"
xMark = "&#x2715;"
questionMark = "&#10067;" # 10068, 9072
bangMark = "&#10071;" # 10069
warningSign = "&#9888;"

repo_base = "https://maven.scijava.org"
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
group_orgs = file2map('group-orgs.txt')

# -- Functions --

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
    return f"<a href=\"{repo_base}/#nexus-search;gav~{g}~{a}~{v}~~\">{v}</a>"

def review_score(c):
    """
    A score based on PRs needing attention (review and/or merge).

    1000 * Count of PRs awaiting review attention.

    How many open PRs (minus `question` and `changes requested` PRs -- esp. PRs
    awaiting review).
    """
    # TODO
    return 0

def support_score(c):
    """
    A score based on issues needing response.

    Think about how engaged issue/PR participants will be to receive a reply at
    this time. Incentivize team answering:
    1. within 24 hours
    2. within 14 days
    3. after 14 days, prefer answering oldest open issues first.

    How many open issues (minus `question` issues).

    V * number of issues awaiting team attention. V varies per issue, based on
    time (engage(H)) since last team member reply. But we may not have
    individual stats per issue. May need to augment github.py to compute more
    stats.
    """
    # TODO
    return 0

def maintenance_score(c):
    """
    A score based on how badly a release needs to be cut.

    100 * <sqrt(D)> where D is the number of days (ceil(lastModified - vetted))
    of datestamp difference.
    """
    # TODO
    return 0

def developer_score(c, developer):
    """
    Total score for this component for the given developer.

    We want to incentivize addressing PRs first, followed by cutting releases,
    followed by bumping versions, followed by addressing remaining issues.
    """
    rs = review_score(c) if 'reviewer' in developer['roles'] else 0
    ss = support_score(c) if 'support' in developer['roles'] else 0
    ms = maintenance_score(c) if 'maintenance' in developer['roles'] else 0
    return rs + ss + ms

def report(status: Sequence[Dict[str, object]]):
    # START HERE: TODO: FIXME: OLD CODE -- update this
    sorted_rows = sorted(status, key=lambda x: f"{x['issues']['org']/x['issues']['repo'] if x['issues'] else ''};{x['groupId']:x['artifactId']}")
    for row in sorted_rows:
        g = row['groupId']
        a = row['artifactId']
        logging.info(f"Processing {g}:{a}")

        if row['issues']:
            issues = row['issues']
            prs = issues['prs']
            drafts = issues['drafts']
            issue_count = issues['count']

            labels = issues['labels']
            bugs = labels.get('bug', 0)
            enhs = labels.get('enhancement', 0)

            issues['assignees']

            milestones = issues['milestones']
            ms_none = milestones.get('none', 0)

            updated = issues['updated'] # TODO: convert GHI timestamp to datetime?

        if row['release']:
            assert g == row['release']['groupId'] and a == row['release']['artifactId']
            bom_version = row['release']['release']
            bom_release_date = row['release']['lastUpdated']
            release_source = f"{repo_base}/content/repositories{row['release']['source']}"
            # ...
        if row['snapshot']:
            assert g == row['snapshot']['groupId'] and a == row['snapshot']['artifactId']
            last_version = row['snapshot']['lastVersion']
            last_updated_date = row['snapshot']['lastUpdated']
            snapshot_source = f"{repo_base}/content/repositories{row['snapshot']['source'}"
            # ...
        if row['team']:
            maintainer_count = len(row['team'].get('maintainer', 0)
            reviewer_count = len(row['team'].get('reviewer', 0)
            support_count = len(row['team'].get('support', 0)
            # ...
        if row['pom']:
            pom = row['pom']
            assert g == pom['groupId'] and a == pom['artifactId']
            ci = pom['ci']
            # TODO: generalize the badge generation; should handle travis-ci.org and travis-ci.com too.
            badge = f"<td class=\"badge\"><a href=\"{ci}\"><img src=\"{ci}/workflows/build-main.yml/badge.svg\"></a></td>"
            issues_url = pom['issues']
            scm_url = pom['scm']
            pom_source = f"{repo_base}/content/repositories{pom['source'}"
            assert last_version == pom['version'] # what if not row['snapshot'] ?

    # Get project metadata
    url = project_url(ga)
    ciBadge = badge(url)

"""
WHAT IS NEEDED FOR TABLE COLUMNS:

Generate the actual results table in HTML.
    - Each table row is a COMPONENT.
    - Components are grouped by REPOSITORY (using rowspan).

Fields of the table are:

<--            Repo scope                            -->   <!--               component scope                         -->
Repository | Build status | Review score | Support score | Maintainance score | Artifact      | Release (BOM -> newest) |

Scores are heuristic calculations of how much attention the repository needs right now.

1. PRs needing merge -- most urgent. creates new commits on main; contributors deserve a reply.
2. cut release -- next most urgent. release ready main branch!
3. bump version -- next step. release won't reach downstream components without this.
4. open issues -- these lead to PRs.

Edge cases:
- What if issueManagement differs across component POMs in the same repository?
- Repositories not part of the BOM, but which we want one row for that repo with review + support scores. hardcoded txt file list?

Filters:
- By person. (Single Team column, Details, listing the team of the component.)
- By GitHub org.
- By groupId.
- Plus a plain text filter?
Is it enough for the first three to just be dropdown list boxes?

Info we need from maven-metadata.xml:
- latest -- newest SNAPSHOT version, only used internally to find the newest POM
- release -- newest release version
- lastUpdated -- timestamp for deciding whether a new release needs to be cut (compare vs newest release timestamp)

Info we need from POM:
- ciManagement/url -- for build badge
- scmManagement/url -- just for linking to the project online like we do now from the Artifact/Repository column
- issueManagement/url -- for where to look for project issues
- roles -- developer ids with each role, for enabling table sorting by priority

For CI badge from ciManagement/url:
- https://travis-ci.org/imagej/ImageJA             -> red X symbol
- https://travis-ci.com/github/imagej/ImageJA      -> travis-ci.com badge
- https://app.travis-ci.com/github/imagej/ImageJA  -> travis-ci.com badge
- https://github.com/imagej/ImageJA/actions        -> github.com actions badge
- Anything else non-empty                          -> question mark symbol (with URL as a link, still)

For repositories on the explicit repositories list (not inferred from components of pom-scijava):
- Some of these have a pom.xml (e.g. bonej-javadoc), some don't (e.g. pyimagej)
- For POM projects, we can extract all the usual info as above. We just need to resolve the POM differently:
  - pom-urls.txt map pointing to the GitHub raw link -- so that we don't rely on anything being deployed to maven.scijava.org
- For non-POM projects:
  - Need to explicitly declare all the info normally harvested from the POM. (CI, SCM, issues, dev roles)
    Where and how should we declare this info? in a YAML or JSON file, perhaps?

- For Python projects, we could glean latest, release, and lastUpdated from SCM... but it's more work... later.
"""

def htmlify(row):
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

def footer():
    with open('footer.html') as f:
        return f.read().strip()

def sort_key(c):
    return f"{x['issues']['org']/x['issues']['repo'] if x['issues'] else ''};{x['groupId']:x['artifactId']}"

def report(status: Sequence[Dict[str, object]]):
    status = sorted(status, key=sort_key)

# Emit the HTML header matter.
    # Python indented multiline strings? Remind myself.
    return f"""
<html>
<head>
<title>SciJava software status</title>
<link type="text/css" rel="stylesheet" href="status.css">
<link rel="icon" type="image/png" href="favicon.png">
<script type="text/javascript" src="sorttable.js"></script>
<script type="text/javascript" src="sortable-badges.js"></script>
</head>
<body onload="makeBadgesSortable()">
<!-- Generated via https://codepo8.github.io/css-fork-on-github-ribbon/ -->
<span id="forkongithub"><a href="https://github.com/scijava/status.scijava.org">Fix me on GitHub</a></span>
<table class="sortable">
<tr>
<th>Artifact</th>
<th>Release</th>
<th>OK</th>
<th>Last vetted</th>
<th>Last updated</th>
<th>OK</th>
<th>Action</th>
<th>Build</th>
</tr>
{"".join(htmlify(c) for c in status)}
</table>
{footer()}
</body>
</html>
"""

if __name__ == '__main__':
    # TODO: arg parsing + usage
    with open("status.json") as f:
        status = json.read(f)
    print(report(status))
