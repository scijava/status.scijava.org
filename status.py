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

def process():
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
            "labels":      Counter([label for issue in issues for label in issue.labels]),
            "milestones":  Counter([issue.milestone if issue.milestone else 'none' for issue in issues]),
            "oldest":      str(min(issue.created_at for issue in issues)) if issues else None,
            "updated":     str(max(issue.updated_at for issue in issues)) if issues else None,
            "assignees":   Counter([assignee for issue in issues for assignee in issue.assignees])
        })

        # what about milestones past due! they are bad

    print(json.dumps(bom, sort_keys=True, indent=4))

# -- Main --

if __name__ == '__main__':
    logging.root.setLevel(logging.INFO)
    result = process()
    if result:
        print(json.dumps(result, sort_keys=True, indent=4))
    else:
        print("Unable to synthesize component status data.")

# ==================
# === NEXT STEPS ===
# ==================
#
# 1.  We aren't using versions:display-dependency-updates anymore. Therefore,
#     we need to apply the rules.xml regex patterns ourselves in maven.py to
#     filter out unwanted versions. Should be straightforward to do in Python.
#
# 2.  Do we need the history of the status table? I don't think we do.
#     So then status.scijava.org should NO LONGER be a GitHub Pages site,
#     but rather just this Python code, plus assets in an assets folder.
#     All on the main branch, no more gh-pages branch.
#
#     Then balinese can run this code as a cron job, and write the
#     output site to the docroot at /var/www/status.scijava.org/
#
# 3.  Sanity check that the datestamp on the discovered SNAPSHOT.pom is very
#     close to the <latest> value -- e.g., for legacy-imglib1, from maven-metadata.xml:
#
#         <lastUpdated>20210702145659</lastUpdated>
#
#     And on the file system:
#
#         /opt/sonatype-work/nexus/storage/snapshots/sc/fiji/legacy-imglib1/1.1.10-SNAPSHOT/legacy-imglib1-1.1.10-20210702.145658-9.pom
#
#     Note that these timestamps are off by 1 second. But close enough!
#
# 4.  Consider reintroducing a step that calls
#     `mvn versions:display-dependency-updates` like newest-releases.sh used to do.
#
#     Reasons to consider doing this, even though it is slow:
#     -   Can apply rules.xml to filter newest versions to regex criteria.
#     -   Might help keep maven.scijava.org proxies up-to-date with upstreams.
#         But it doesn't invalidate the server-side caches for proxied
#         artifacts; gotta do that too to be certain to have the latest.
#
# 5.  In the meantime: if the (2) sanity check fails, it means we don't have a
#     POM we're confident is the best one. In that case, the HTML table should
#     show question mark symbols in the columns normally pulled from the POM.
#
# 6.  Under what circumstances would we want to trigger an immediate rebuild of
#     status.scijava.org? Ideally whenever pom-scijava changes. But also every
#     hour. Or 30 minutes? or 10 minutes? Releases happen asynchronously!
#     Probably just running it via cron every 30 minutes is good enough.
#     But it would be great to have instant updates after a pom-scijava push.
