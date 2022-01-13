#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# maven.py
# ------------------------------------------------------------------------
# Supporting library for harvesting metadata about Maven components.
# Requires direct access to the backing storage of the repositories.
#
# When run from the command line, generates a data structure with information
# about the components and repositories of the SciJava component collection.

import json, os, pathlib, re, sys
from datetime import datetime
from typing import Any, Dict, Optional, List, Sequence
from xml.etree import ElementTree as ET

# -- Constants --

storage = "/opt/sonatype-work/nexus/storage"
release_repos = ["releases", "thirdparty", "sonatype", "central", "ome-releases"]
snapshot_repos = ["snapshots", "sonatype-snapshots", "ome-snapshots"]

ts_allowance = 10 # maximum seconds difference in SNAPSHOT timestamp

# -- Classes --

class XML:

    def __init__(self, source):
        self.source = source
        self.tree = ET.parse(source)
        XML._strip_ns(self.tree.getroot())

    def elements(self, path: str) -> List[ET.Element]:
        return self.tree.findall(path)

    def value(self, path: str) -> Optional[str]:
        el = self.elements(path)
        assert len(el) <= 1
        return None if len(el) == 0 else el[0].text

    @staticmethod
    def _strip_ns(el: ET.Element) -> None:
        """
        Remove namespace prefixes from elements and attributes.
        Credit: https://stackoverflow.com/a/32552776/1207769
        """
        if el.tag.startswith("{"):
            el.tag = el.tag[el.tag.find("}")+1:]
        for k in list(el.attrib.keys()):
            if k.startswith("{"):
                k2 = k[k.find("}")+1:]
                el.attrib[k2] = el.attrib[k]
                del el.attrib[k]
        for child in el:
            XML._strip_ns(child)

class MavenPOM(XML):

    @property
    def groupId(self) -> Optional[str]:
        return self.value("groupId") or self.value("parent/groupId")

    @property
    def artifactId(self) -> Optional[str]:
        return self.value("artifactId")

    @property
    def version(self) -> Optional[str]:
        return self.value("version") or self.value("parent/version")

    @property
    def scmURL(self) -> Optional[str]:
        return self.value("scm/url")

    @property
    def issuesURL(self) -> Optional[str]:
        return self.value("issueManagement/url")

    @property
    def ciURL(self) -> Optional[str]:
        return self.value("ciManagement/url")

    @property
    def developers(self) -> List[Dict[str, Any]]:
        devs = []
        for el in self.elements("developers/developer"):
            dev: Dict[str, Any] = {}
            for child in el:
                if len(child) == 0:
                    dev[child.tag] = child.text
                else:
                    if child.tag == 'properties':
                        dev[child.tag] = {grand.tag: grand.text for grand in child}
                    else:
                        dev[child.tag] = [grand.text for grand in child]
            devs.append(dev)
        return devs

class MavenMetadata(XML):

    @property
    def groupId(self) -> Optional[str]:
        try:
            return self.value("groupId")
        except Exception:
            return self.value("parent/groupId")

    @property
    def artifactId(self) -> Optional[str]:
        return self.value("artifactId")

    @property
    def lastUpdated(self) -> Optional[int]:
        result = self.value("versioning/lastUpdated")
        return None if result is None else int(result)

    @property
    def latest(self) -> Optional[str]:
        # WARNING: The <latest> value is often wrong, for reasons I don't know.
        # However, the last <version> under <versions> has the correct value.
        # Consider using lastVersion instead of latest.
        return self.value("versioning/latest")

    @property
    def lastVersion(self) -> Optional[str]:
        vs = self.elements("versioning/versions/version")
        return None if len(vs) == 0 else vs[-1].text

    @property
    def release(self) -> Optional[str]:
        return self.value("versioning/release")

class MavenComponent:

    def __init__(self, g: str, a: str):
        self.groupId = g
        self.artifactId = a
        self.release = MavenComponent._metadata(release_repos, g, a)
        self.snapshot = MavenComponent._metadata(snapshot_repos, g, a)
        self.pom: Optional[MavenPOM] = None
        if self.snapshot and self.snapshot.lastVersion:
            # Get the newest POM possible, based on last updated SNAPSHOT.
            self.pom = MavenComponent._pom(snapshot_repos, g, a, v=self.snapshot.lastVersion,
                ts=str(self.snapshot.lastUpdated))
        elif self.release and self.release.lastVersion:
            # Get the POM of the newest release.
            self.pom = MavenComponent._pom(release_repos, g, a, v=self.release.lastVersion)

    @staticmethod
    def _metadata(repos: Sequence[str], g: str, a: str) -> Optional[MavenMetadata]:
        suffix = f"{g.replace('.', '/')}/{a}/maven-metadata.xml"
        best = None
        for repo in repos:
            path = f"{storage}/{repo}/{suffix}"
            if os.path.exists(path):
                m = MavenMetadata(path)
                if best is None or (m.lastUpdated is not None and m.lastUpdated > best.lastUpdated):
                    best = m
        return best

    @staticmethod
    def _pom(repos, g: str, a: str, v: str, ts=None) -> Optional[MavenPOM]:
        gav_path = f"{g.replace('.', '/')}/{a}/{v}"
        if v.endswith("-SNAPSHOT"):
            # Find snapshot POM with matching timestamp.
            assert ts is not None
            dt_requested = ts2dt(ts)
            pom_prefix = f"{a}-{v[:-9]}" # artifactId-version minus -SNAPSHOT
            for repo in repos:
                d = pathlib.Path(f"{storage}/{repo}/{gav_path}")
                for f in d.glob(f"{pom_prefix}-*.pom"):
                    m = re.match(pom_prefix + "-(\d{8}\.\d{6})-\d+\.pom", f.name)
                    if not m: continue # ignore weirdly named POM
                    dt_actual = ts2dt(m.group(1))
                    if abs(dt_requested - dt_actual).seconds <= ts_allowance:
                        # Timestamp is within tolerance! Found it!
                        return MavenPOM(str(f))
        else:
            # Find release POM.
            suffix = f"{gav_path}/{a}-{v}.pom"
            for repo in repos:
                path = f"{storage}/{repo}/{suffix}"
                if os.path.exists(path):
                    return MavenPOM(path)
        return None

# -- Functions --

def ts2dt(ts: str) -> datetime:
    """
    Converts Maven-style timestamp strings into Python datetime objects.

    Valid forms:
    * 20210702144918 (seen in <lastUpdated> in maven-metadata.xml)
    * 20210702.144917 (seen in deployed SNAPSHOT filenames)
    """
    m = re.match("(\d{4})(\d\d)(\d\d)\.?(\d\d)(\d\d)(\d\d)", ts)
    if not m: raise ValueError(f"Invalid timestamp: {ts}")
    return datetime(*map(int, m.groups())) #noqa

def resource_path(source: str) -> str:
    return None if source is None else source[len(storage):]

def status(c: MavenComponent) -> Dict[str, Any]:
    """
    Gathers information from Maven about the given groupId:artifactId.
    """
    record: Dict[str, Any] = {
        "groupId": c.groupId,
        "artifactId": c.artifactId
    }
    record["release"] = None if c.release is None else {
        "source": resource_path(c.release.source),
        "groupId": c.release.groupId,
        "artifactId": c.release.artifactId,
        "lastUpdated": c.release.lastUpdated,
        "latest": c.release.latest,
        "lastVersion": c.release.lastVersion,
        "release": c.release.release,
    }
    record["snapshot"] = None if c.snapshot is None else {
        "source": resource_path(c.snapshot.source),
        "groupId": c.snapshot.groupId,
        "artifactId": c.snapshot.artifactId,
        "lastUpdated": c.snapshot.lastUpdated,
        "latest": c.snapshot.latest,
        "lastVersion": c.snapshot.lastVersion,
        "release": c.snapshot.release,
    }
    record["pom"] = None if c.pom is None else {
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

def matches(g: str, a: str, patterns: Sequence[str]) -> bool:
    return not patterns or any(re.match(pat, f"{g}:{a}") for pat in patterns)

def process(patterns=[]) -> Optional[List[Dict[str, Any]]]:
    g = "org.scijava"
    a = "pom-scijava"
    psj = MavenComponent(g, a)

    if not psj.release and not psj.snapshot and not psj.pom:
        return None

    records = []

    if matches(g, a, patterns):
        records.append(status(psj))

    if not psj.pom:
        return records

    for dep in psj.pom.elements("dependencyManagement/dependencies/dependency"):
        g = dep.find("groupId").text #noqa
        a = dep.find("artifactId").text #noqa

        if matches(g, a, patterns):
            c = MavenComponent(g, a)
            records.append(status(c))

    return records

def main(args: Sequence[str]):
    result = process(args)
    if result:
        print(json.dumps(result, sort_keys=True, indent=4))
    else:
        print("This script must be run from the SciJava Maven server.")

if __name__ == '__main__':
    main(sys.argv[1:])
