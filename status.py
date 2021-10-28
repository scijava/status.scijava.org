#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# status.py
# ------------------------------------------------------------------------
# Aggregates information for components of the SciJava component collection,
# using multiple sources, including Maven repositories and GitHub.

import json, logging, re
from collections import Counter
from pathlib import Path

import github, maven

# -- Constants --

cache_dir = Path('.cache')

# -- Functions --

def issues_repo(pom):
    """
    If this POM record declares GitHub Issues for its issue management,
    return the GitHub (org, repo) pair. Otherwise, return (None, None).
    """
    if pom['issues'] is None: return None, None
    m = re.match('https?://github.com/([^/]+)/([^/]+)/issues', pom['issues'])
    if not m: return None, None # does not use GitHub Issues
    return m.group(1), m.group(2)

def fetch_issues(orgs):
    ghi = github.GitHubIssues()
    query = "+".join(f"user:{org}" for org in orgs)
    ghi.download(query)
    return ghi

def run():
    # Get all the juicy details from the Maven metadata.
    bom_file = cache_dir / 'maven.json'
    if bom_file.is_file():
        logging.info(f"Reading Maven metadata from {bom_file}...")
        with open(bom_file) as f:
            bom = json.loads(f.read())
    else:
        logging.info("Reading Maven metadata from local repository storage...")
        bom = maven.process()
        if bom and cache_dir.is_dir():
            logging.info(f"Writing Maven metadata to {bom_file}...")
            with open(bom_file, "w") as f:
                json.dump(bom, f, sort_keys=True, indent=4)
    if not bom:
        logging.error("This script must be run from the SciJava Maven server,\n"
                      f"or you must have a {bom_file} with cached metadata.")
        sys.exit(1)

    # Augment the BOM records with team information.
    logging.info("Augmenting BOM with team info...")
    for c in bom:
        c["team"] = {}
        if not c["pom"]: continue

        # Populate the team section: map developer roles to list of developer ids.
        for dev in c["pom"]["developers"]:
            if not "roles" in dev: continue # developer has no roles
            if not "id" in dev: continue # developer has no id
            for role in dev["roles"]:
                if role in c["team"]:
                    c["team"][role].append(dev["id"])
                else:
                    c["team"][role] = [dev["id"]]

    # Augment the BOM records with statistics about issues.
    logging.info(f"Cataloging usages of GitHub issues...")
    for c in bom:
        c["issues"] = None
        if not c["pom"]: continue

        # Populate a barebones issues section, if component uses GitHub Issues.
        org, repo = issues_repo(c["pom"])
        if org and repo:
            c["issues"] = {"org": org, "repo": repo}

    # Compile a list of orgs containing any repository that:
    # 1. Uses GitHub Issues; and
    # 2. Has any developer with reviewer or support role.
    orgs = {c["issues"]["org"] for c in bom \
            if c["issues"] and any(role in c["team"] for role in ["reviewer", "support"])}
    orgs = list(orgs)
    orgs.sort()

    # Retrieve all the open issues for those orgs.
    logging.info(f"Loading issues for orgs: {orgs}")
    ghi = github.GitHubIssues()
    issues_file = cache_dir / 'issues.json'
    if issues_file.is_file():
        logging.info(f"Reading GitHub issues from {issues_file}...")
        ghi.load(issues_file)
    else:
        logging.info("Fetching issues from GitHub...")
        ghi = fetch_issues(orgs)
        if cache_dir.is_dir():
            logging.info(f"Writing GitHub issues to {issues_file}...")
            ghi.save(issues_file)
    logging.info(f"Retrieved {len(ghi.issues())} issues")

    # Augment the BOM records with statistics about issues.
    logging.info(f"Augmenting BOM with issues info...")
    for c in bom:
        if not c["issues"]: continue # Component does not use GitHub Issues.

        issues = ghi.repo(c["issues"]["org"], c["issues"]["repo"]).issues()

        c["issues"].update({
            "count":       len(issues),
            "prs":         sum(1 for issue in issues if issue.is_pr),
            "drafts":      sum(1 for issue in issues if issue.is_draft),
            "unscheduled": sum(1 for issue in issues if issue.milestone == 'unscheduled'),
            "labels":      Counter([label for issue in issues for label in issue.labels]),
            "milestones":  Counter([issue.milestone if issue.milestone else 'none' for issue in issues]),
            "oldest":      str(min(issue.created_at for issue in issues)) if issues else None,
            "updated":     str(max(issue.updated_at for issue in issues)) if issues else None,
            "assignees":   Counter([assignee for issue in issues for assignee in issue.assignees])
        })

    print(json.dumps(bom, sort_keys=True, indent=4))

# -- Main --

if __name__ == '__main__':
    logging.root.setLevel(logging.INFO)
    run()


## CTR START HERE -
# Review these notes from earlier, keep what's useful, throw the rest away.

# - maven_poms.py, adapted from pom-scijava's tests/generate-mega-melt.py, generates a pom.xml with only allow-listed groupIds.
#   From there, we can call "mvn -DexcludeTransitive=true dependency:copy-dependencies" to grab all POMs at once into target/dependency.
#   Unfortunately, Maven still does (at least) one web request per POM, and it takes a long time to check all these GAs for updates.
# - Much faster would be to do it on the server side, on balinese. We could use a python script that looks directly at the file system
#   of /opt/sonatype-work/nexus/storage/snapshots/ for maven-metadata.xml (for <latest> and <lastUpdated> tags), and also
#   extracts data from the POM at /opt/sonatype-work/nexus/storage/snapshots/<groupId>/<artifactId>/<latest>/*.pom
#   (should sanity check that the datestamp on the discovered SNAPSHOT.pom is very close to the <latest> value -- e.g., for legacy-imglib1:
#       <lastUpdated>20210702145659</lastUpdated>
#       /opt/sonatype-work/nexus/storage/snapshots/sc/fiji/legacy-imglib1/1.1.10-SNAPSHOT/legacy-imglib1-1.1.10-20210702.145658-9.pom
# - So then we need to write this JSON document to something like maven.scijava.org/status.scijava.org.json, and it can curl that down
#   and generate the table from there? Do we need such a separation? We could just have balinese serve that domain, too.
# - We want to cover edge cases, though:
#   - What if the sanity check above fails? I.e. we don't have a POM we're confident is the best one?
#     Then we show question mark symbols in the columns normally pulled from the POM: build badge

# Info we need from maven-metadata.xml:
# - latest -- newest SNAPSHOT version, only used internally to find the newest POM
# - release -- newest release version
# - lastUpdated -- timestamp for deciding whether a new release needs to be cut (compare vs newest release timestamp)

# Info we need from POM:
# - ciManagement/url -- for build badge
# - scmManagement/url -- just for linking to the project online like we do now from the Artifact/Repository column
# - issueManagement/url -- for where to look for project issues
# - roles -- developer ids with each role, for enabling table sorting by priority

# For CI badge from ciManagement/url:
# - https://travis-ci.org/imagej/ImageJA             -> red X symbol
# - https://travis-ci.com/github/imagej/ImageJA      -> travis-ci.com badge
# - https://app.travis-ci.com/github/imagej/ImageJA  -> travis-ci.com badge
# - https://github.com/imagej/ImageJA/actions        -> github.com actions badge
# - Anything else non-empty                          -> question mark symbol (with URL as a link, still)

# For repositories on the explicit repositories list (not inferred from components of pom-scijava):
# - Some of these have a pom.xml (e.g. bonej-javadoc), some don't (e.g. pyimagej)
# - For POM projects, we can extract all the usual info as above. We just need to resolve the POM differently:
#   - pom-urls.txt map pointing to the GitHub raw link -- so that we don't rely on anything being deployed to maven.scijava.org
# - For non-POM projects:
#   - Need to explicitly declare all the info normally harvested from the POM. (CI, SCM, issues, dev roles)
#     Where and how should we declare this info? in a YAML or JSON file, perhaps?

# - For Python projects, we could glean latest, release, and lastUpdated from SCM... but it's more work... later.

# - balinese can run a cron job generating maven.scijava.org/status.json

# Questions to answer:
# - How often should balinese regenerate the status.json ?
# - Under what circumstances would we want to trigger an immediate rebuild of status.scijava.org? Ideally whenever pom-scijava changes...

# CTR FIXME - Instead of writing this newest-releases file into .cache,
# we could instead read
#   ~/.m2/repository/$g/$a/maven-metadata-scijava-mirror.xml
# for each component on the list.
# And we can also look for
#   ~/.m2/repository/$g/$a/$v/$a-$v.pom
# for v of the newest release.

# So the steps are:
# 0. Get the list of components into a dict
# 1. Refresh maven-metadata xml (versions:display-dependency-updates) and add it to the dict
# 2. Refresh pom files
#    - use BOM release version POM?
#    - or latest release version POM?
#    - or latest POM on main/master branch of listed scm?
#    - what is the fastest way to get and cache all these POMs?
#        - mvn dependency:get -Dartifact=net.imagej:imagej-common:0.34.1:pom only gets the POM, not the JAR (whew!)
#          But do we want to do that for every single artifact?
#        - if we're reading them from GitHub, we should save the etag from response headers, and check 'curl -I' next time...
#          But will this actually be faster? The poms are so small.
# 3. Read desired information from maven-metadata and POMs, populating dict
# 4. Using contents of dict, generate the query to use for GitHub Issues
# 5. Make the GitHub Issues query/ies, caching resultant JSON.
# 6. Generate the actual results table in HTML.
#    - Each table row is a COMPONENT.
#    - Components are grouped by REPOSITORY (using rowspan).
#
# Fields of the table are:
#
# <--            Repo scope                            -->   <!--               component scope                         -->
# Repository | Build status | Review score | Support score | Maintainance score | Artifact      | Release (BOM -> newest) |
#

# Score is a heuristic calculation of how much attention the repository needs right now. Factors include:
# 1. PRs needing merge -- most urgent. creates new commits on main; contributors deserve a reply.
# 2. cut release -- next most urgent. release ready main branch!
# 3. bump version -- next step. release won't reach downstream components without this.
# 4. open issues -- these lead to PRs.

# We want to incentivize addressing PRs first, followed by cutting releases,
# followed by bumping versions, followed by addressing remaining issues.
# Therefore, we score as follows:
#
#   1000 * Count of PRs awaiting maintainer attention.
# +  100 * <sqrt(D)> where D is the number of days (ceil(lastModified - vetted)) of datestamp difference.
# +   10 * 
# +    V * number of issues awaiting team attention. V varies per issue, based on time (engage(H)) since last team member reply.

# Team roles that matter here: support, reviewer, maintainer.
# - reviewers scored on PRs needing review/merge
# - support scored on issues needing response
# - maintainers scored on releases needing to be cut

# The engage function tries to model community engagement:
# - Think about how engaged issue/PR participants will be to receive a reply at this time.
# - Incentivize team answering:
#   1. within 24 hours
#   2. within 14 days
#   3. after 14 days, prefer answering oldest open issues first.

# - how many open issues (minus `question` issues)
# - how many open PRs (minus `question` and `changes requested` PRs -- esp. PRs awaiting review)

# Edge cases:
# - What if issueManagement differs across component POMs in the same repository?
# - Repositories not part of the BOM, but which we want one row for that repo with review + support scores. hardcoded txt file list?

# Filters:
# - By person. (Single Team column, Details, listing the team of the component.)
# - By GitHub org.
# - By groupId.
# - Plus a plain text filter?
# Is it enough for the first three to just be dropdown list boxes?

