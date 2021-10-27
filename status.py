#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# status.py
# ------------------------------------------------------------------------
# Generates a data structure with information about the components
# and repositories of the SciJava component collection.

import json, re, sys

import maven

def resource_path(source):
    return None if source is None else source[len(maven.storage):]

def status(c):
    """
    Gathers information from Maven about the given groupId:artifactId.
    """
    record = {
        "groupId": c.groupId,
        "artifactId": c.artifactId
    }
    if c.release:
        record["release"] = {
            "source": resource_path(c.release.source),
            "groupId": c.release.groupId,
            "artifactId": c.release.artifactId,
            "lastUpdated": c.release.lastUpdated,
            "latest": c.release.latest,
            "lastVersion": c.release.lastVersion,
            "release": c.release.release,
        }
    if c.snapshot:
        record["snapshot"] = {
            "source": resource_path(c.snapshot.source),
            "groupId": c.snapshot.groupId,
            "artifactId": c.snapshot.artifactId,
            "lastUpdated": c.snapshot.lastUpdated,
            "latest": c.snapshot.latest,
            "lastVersion": c.snapshot.lastVersion,
            "release": c.snapshot.release,
        }
    if c.pom:
        record["pom"] = {
            "source": resource_path(c.pom.source),
            "groupId": c.pom.groupId,
            "artifactId": c.pom.artifactId,
            "version": c.pom.version,
            "scm": c.pom.scmURL,
            "issues": c.pom.issuesURL,
            "ci": c.pom.ciURL,
            "developers": c.pom.developers,
        }
    return record

def matches(g, a, patterns):
    return not patterns or any(re.match(pat, f"{g}:{a}") for pat in patterns)

def process(patterns=[]):
    g = "org.scijava"
    a = "pom-scijava"
    psj = maven.MavenComponent(g, a)

    if not psj.release and not psj.snapshot and not psj.pom:
        return None

    records = []

    if matches(g, a, patterns):
        records.append(status(psj))

    for dep in psj.pom.elements("dependencyManagement/dependencies/dependency"):
        g = dep.find("groupId").text
        a = dep.find("artifactId").text

        if matches(g, a, patterns):
            c = maven.MavenComponent(g, a)
            records.append(status(c))

    return records

if __name__ == '__main__':
    result = process(sys.argv[1:])
    if result:
        print(json.dumps(result, sort_keys=True, indent=4))
    else:
        print("This script must be run from the SciJava Maven server.")
