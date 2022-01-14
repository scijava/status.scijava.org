#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# report.py
# ------------------------------------------------------------------------
# Generates an HTML report of the release status of all
# components in the SciJava BOM (org.scijava:pom-scijava).

import datetime, json, re, sys
from pathlib import Path
from typing import Any, Collection, Dict, List, Optional, Sequence, Union

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

def file2map(filepath: Union[str, Path], sep: str = ' '):
    with open(filepath) as f:
        pairs = [line.strip().split(sep, 1) for line in f.readlines()]
    return {pair[0]: pair[1] for pair in pairs}

badge_overrides = file2map('ci-badges.txt')
timestamps = file2map('timestamps.txt')

def get(data: Dict[Any, Any], *args):
    """
    Convenience function for null-safe data attribute access.
    """
    for arg in args:
        if data is None or not arg in data: return None
        data = data[arg]
    return data

# -- Functions --

def timestamp_override(g: str, a: str) -> Optional[datetime.datetime]:
    """
    Gets the timestamp when a component was last vetted.

    Sometimes, we know a new snapshot has no release-worthy changes since
    the last release. In this scenario, we can record the last time we
    checked a given component in the timestamps.txt file.

    This also gives us a hedge against problems with the Maven metadata,
    such as that particular G:A not being present in the remote repository
    for any reason (in which case, this function returns None).
    """
    ts = timestamps.get(f'{g}:{a}', None)
    return ts2dt(ts) if ts else None

def review_score(c: Dict[str, Any]) -> int:
    """
    A score based on PRs needing attention (review and/or merge).

    1000 * Count of PRs awaiting review attention.

    How many open PRs (minus `question` and `changes requested` PRs -- esp. PRs
    awaiting review).
    """
    issues = get(c, 'issues')
    if not issues: return 0

    # TODO: Incorporate labels and "changes requested" status into computation.
    open_prs = get(issues, 'prs') or 0
    draft_prs = get(issues, 'drafts') or 0
    return 1000 * (open_prs - draft_prs)

def support_score(c: Dict[str, Any]) -> int:
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
    issues = get(c, 'issues')
    if not issues: return 0

    # TODO: Consider issue ages, reply status, milestone breakdown.
    open_issues = get(issues, 'count') or 0
    question_issues = get(issues, 'labels', 'question') or 0
    bugs = get(issues, 'labels', 'bug') or 0
    no_milestone = get(issues, 'milestones', 'none') or 0
    return 10 * (open_issues - question_issues) + 100 * bugs + 25 * no_milestone

def maintenance_score(c: Dict[str, Any]) -> int:
    """
    A score based on how badly a release needs to be cut.

    Score is the number of seconds between last vetted and last updated times.
    """

    # Discern timestamps for this component.
    #
    # Each component is "vetted" either by:
    #   A) being released; or
    #   B) adding an override to timestamps.txt.
    # Our goal here is to detect whether the component has changed since
    # the most recent release (not the release listed in the BOM).
    rlu = get(c, 'release', 'lastUpdated')
    release_timestamp = ts2dt(str(rlu)) if rlu else datetime0
    manual_timestamp = timestamp_override(c['groupId'], c['artifactId'])
    last_vetted = max(release_timestamp, manual_timestamp or datetime0)

    if last_vetted == 0:
        # Component status is broken -- maintainer needs to fix it!
        return 9999999999999

    slu = get(c, 'snapshot', 'lastUpdated')
    last_updated = ts2dt(str(slu)) if slu else datetime0
    delta = last_updated - last_vetted
    return max(0, int(delta.total_seconds()))

def developer_score(c: Dict[str, Any], dev: Dict[str, Any]) -> Optional[int]:
    """
    Total score for this component for the given developer.

    We want to incentivize addressing PRs first, followed by cutting releases,
    followed by bumping versions, followed by addressing remaining issues.
    """
    roles = get(dev, 'roles')
    if not roles: return None # Not a SciJava developer entry.

    is_reviewer = 'reviewer' in roles
    is_support = 'support' in roles
    is_maintainer = 'maintainer' in roles
    if not is_reviewer and not is_support and not is_maintainer:
        # Developer is not responsible for this component in any way.
        return None

    rs = review_score(c) if is_reviewer else 0
    ss = support_score(c) if is_support else 0
    ms = maintenance_score(c) if is_maintainer else 0
    return rs + ss + ms

"""
WHAT IS NEEDED FOR TABLE COLUMNS:

Generate the actual results table in HTML.
    - Each table row is a COMPONENT.
    - Components are grouped by REPOSITORY (using rowspan).

Fields of the table are:

<--            Repo scope                            -->   <!--               component scope                         -->
Repository | Build status | Review score | Support score | Maintainance score | Artifact      | Release |

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

def release_link(g: str, a: str, v: str) -> str:
    return f"<a href=\"{repo_base}/#nexus-search;gav~{g}~{a}~{v}~~\">{v}</a>"

def col_repository(c: Dict[str, Any]) -> str:
    scm = get(c, 'pom', 'scm')
    return scm if scm else '-'

def col_build_status(c: Dict[str, Any]) -> str:
    ga = f"{c['groupId']}:{c['artifactId']}"
    if ga in badge_overrides:
        return badge_overrides[ga]
    ci = get(c, 'pom', 'ci')
    if not ci: return "-"
    if re.match("https://github.com/[^/]*/[^/]*/actions", ci):
        return f"<a href=\"{ci}\"><img src=\"{ci}/workflows/build-main.yml/badge.svg\"></a>"
    # TODO: Case for travis-ci.com. Any others?
    return "-"

def col_artifact(c: Dict[str, Any]) -> str:
    return f"{c['groupId']}:{c['artifactId']}"

def col_release(c: Dict[str, Any]) -> str:
    g = c['groupId']
    a = c['artifactId']
    bom_version = get(c, 'release', 'release') # FIXME: status.json doesn't have it! See FIXME in maven.py.
    newest_release = get(c, 'release', 'lastVersion')
    # Changes since vetted (replace space with T):
    # - https://github.com/scijava/scijava-common/commits/master?since=2021-09-09T10:05:24
    # Changes since release:
    # - https://github.com/scijava/scijava-common/compare/scijava-common-2.87.0...master
    # need to know which branch is HEAD (main/master/etc)
    # Should we mark stale timestamp overrides at all? They don't hurt anything; red highlight is annoying.
    if bom_version == newest_release:
        return release_link(g, a, newest_release)
    return release_link(g, a, bom_version) + " &rarr; " + release_link(g, a, newest_release)

class Field:
    def __init__(self, value, classes=[]):
        self.value = value
        self.classes = " ".join(classes)

def compute_fields(c: Dict[str, Any]) -> Dict[str, Field]:
    """
    Computes report fields for the given component.
    Field names across components may differ.

    :param c: The component for which fields will be computed.
    """
    result = {
        "Repository":        Field(col_repository(c)),
        "Build status":      Field(col_build_status(c)),
        "Review score":      Field(str(review_score(c))),
        "Support score":     Field(str(support_score(c))),
        "Maintenance score": Field(str(maintenance_score(c))),
        "Artifact":          Field("Artifact", col_artifact(c)),
        "Release":           Field("Release", col_release(c)),
    }
    devs = get(c, 'pom', 'developers')
    if devs:
        for dev in devs:
            score = developer_score(c, dev)
            if score is not None:
                dev_id = get(dev, 'id') or get(dev, 'name') or '~MYSTERIOUS NINJA~'
                classes = ['dev-' + css_class(dev_id)]
                result[dev_id] = Field(str(score), classes)
    return result

def css_class(s: str) -> str:
    return re.sub('[^0-9A-Za-z]', '-', s)

def row(names: Collection[str], fields: Dict[str, Field]) -> str:
    """
    Emits HTML for a table row.

    :param names: Field names, aligned with the table's column headers.
    :param fields: dictionary of field names to field values.
    """
    artifact = fields["Artifact"].value
    g = artifact[:artifact.find(":")]
    a = artifact[artifact.find(":")+1:]
    columns = "".join(f"<td class=\"{css_class(name)}\">{fields.get(name, '')}</td>\n" for name in names)
    return f"<tr class=\"g-{css_class(g)} a-{css_class(a)}\">\n{columns}</tr>\n"

def _component_sort_key(c: Dict[str, Any]):
    """
    Sort components by:
    1. issues org/repo slug
    2. groupId
    3. artifactId
    """
    org: str = get(c, 'issues', 'org')
    repo: str = get(c, 'issues', 'repo')
    slug = f"{org}/{repo}" if org and repo else ''
    return f"{slug};{c['groupId']}:{c['artifactId']}"

def report(status: Sequence[Dict[str, Any]]) -> str:
    # Compute the fields (i.e. column names and values) per component.
    table: List[Dict[str, Field]] = [compute_fields(c) for c in sorted(status, key=_component_sort_key)]

    # Column headers are a union of field names across all components.
    # NB: It's theoretically possible that the same field could have different
    # classes at different table rows, but in practice it should never happen.
    headers = {field_name: field.classes for fields in table for field_name, field in fields.items()}

    # Generate the major chunks of HTML.
    html_headers = "\n".join(f"<th class=\"{classes}\">" + name + "</th>" for name, classes in headers.items())
    html_table_rows = "".join(row(headers, table_row) for table_row in table)
    with open('footer.html') as f:
        html_footer = f.read().strip()

    html_dev_selector = "<p>\nDeveloper:\n<select id=\"developer\" onchange=\"refresh()\">\n" + \
        "\n".join(f"<option value=\"{dev_id}\">{dev_id}</option>" for dev_id in headers) + \
        "</select>\n</p>\n"

    return re.sub("\n +", "\n", f"""
    <html>
    <head>
    <title>SciJava software status</title>
    <link type="text/css" rel="stylesheet" href="status.css">
    <link rel="icon" type="image/png" href="favicon.png">
    <script type="text/javascript" src="sorttable.js"></script>
    <script type="text/javascript" src="sortable-badges.js"></script>
    <script type="text/javascript" src="table-filters.js"></script>
    </head>
    <body onload="makeBadgesSortable()">
    <!-- Generated via https://codepo8.github.io/css-fork-on-github-ribbon/ -->
    <span id="forkongithub"><a href="https://github.com/scijava/status.scijava.org">Fix me on GitHub</a></span>
    {html_dev_selector}
    <table class="sortable">
    <tr>
    {html_headers}
    </tr>
    {html_table_rows}
    </table>
    {html_footer}
    </body>
    </html>
    """)

def main(args: Sequence[str]):
    # TODO: arg parsing + usage
    with open("status.json") as f:
        status = json.loads(f.read())
    print(report(status))

if __name__ == '__main__':
    main(sys.argv[1:])
