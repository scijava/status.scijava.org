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

import datetime, logging, os, pathlib, re
import xml.etree.ElementTree as ET

storage = "/opt/sonatype-work/nexus/storage"
release_repos = ["releases", "thirdparty", "sonatype", "central", "ome-releases"]
snapshot_repos = ["snapshots", "sonatype-snapshots", "ome-snapshots"]

ts_allowance = 10 # maximum seconds difference in SNAPSHOT timestamp

class XML:

    def __init__(self, source):
        self.source = source
        self.tree = ET.parse(source)
        XML._strip_ns(self.tree.getroot())

    def elements(self, path):
        return self.tree.findall(path)

    def value(self, path):
        el = self.elements(path)
        assert len(el) <= 1
        return None if len(el) == 0 else el[0].text

    @staticmethod
    def _strip_ns(el):
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
    def groupId(self):
        return self.value("groupId") or self.value("parent/groupId")

    @property
    def artifactId(self):
        return self.value("artifactId")

    @property
    def version(self):
        return self.value("version") or self.value("parent/version")

    @property
    def scmURL(self):
        return self.value("scm/url")

    @property
    def issuesURL(self):
        return self.value("issueManagement/url")

    @property
    def ciURL(self):
        return self.value("ciManagement/url")

    @property
    def developers(self):
        devs = []
        for el in self.elements("developers/developer"):
            dev = {}
            for child in el:
                if len(child) == 0: dev[child.tag] = child.text
                else:
                    if child.tag == 'properties':
                        dev[child.tag] = {grand.tag: grand.text for grand in child}
                    else:
                        dev[child.tag] = [grand.text for grand in child]
            devs.append(dev)
        return devs

class MavenMetadata(XML):

    @property
    def groupId(self):
        try:
            return self.value("groupId")
        except Exception:
            return self.value("parent/groupId")

    @property
    def artifactId(self):
        return self.value("artifactId")

    @property
    def lastUpdated(self):
        result = self.value("versioning/lastUpdated")
        return None if result is None else int(result)

    @property
    def latest(self):
        # WARNING: The <latest> value is often wrong, for reasons I don't know.
        # However, the last <version> under <versions> has the correct value.
        # Consider using lastVersion instead of latest.
        return self.value("versioning/latest")

    @property
    def lastVersion(self):
        vs = self.elements("versioning/versions/version")
        return None if len(vs) == 0 else vs[-1].text

    @property
    def release(self):
        return self.value("versioning/release")

class MavenComponent:

    def __init__(self, g, a):
        self.groupId = g
        self.artifactId = a
        self.release = MavenComponent._metadata(release_repos, g, a)
        self.snapshot = MavenComponent._metadata(snapshot_repos, g, a)
        if self.snapshot:
            # Get the newest POM possible, based on last updated SNAPSHOT.
            self.pom = MavenComponent._pom(snapshot_repos, g, a, v=self.snapshot.lastVersion,
                ts=str(self.snapshot.lastUpdated))
        elif self.release:
            # Get the POM of the newest release.
            self.pom = MavenComponent._pom(release_repos, g, a, v=self.release.lastVersion)
        else:
            self.pom = None

    @staticmethod
    def _metadata(repos, g, a):
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
    def _ts2dt(ts):
        """
        Converts Maven-style timestamp strings into Python datetime objects.

        Valid forms:
        * 20210702144918 (seen in <lastUpdated> in maven-metadata.xml)
        * 20210702.144917 (seen in deployed SNAPSHOT filenames)
        """
        m = re.match("(\d{4})(\d\d)(\d\d)\.?(\d\d)(\d\d)(\d\d)", ts)
        if not m: raise ValueError(f"Invalid timestamp: {ts}")
        return datetime.datetime(*map(int, m.groups()))

    @staticmethod
    def _pom(repos, g, a, v, ts=None):
        gav_path = f"{g.replace('.', '/')}/{a}/{v}"
        if v.endswith("-SNAPSHOT"):
            # Find snapshot POM with matching timestamp.
            assert ts is not None
            dt_requested = MavenComponent._ts2dt(ts)
            pom_prefix = f"{a}-{v[:-9]}" # artifactId-version minus -SNAPSHOT
            for repo in repos:
                d = pathlib.Path(f"{storage}/{repo}/{gav_path}")
                for f in d.glob(f"{pom_prefix}-*.pom"):
                    m = re.match(pom_prefix + "-(\d{8}\.\d{6})-\d+\.pom", f.name)
                    if not m: continue # ignore weirdly named POM
                    dt_actual = MavenComponent._ts2dt(m.group(1))
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
