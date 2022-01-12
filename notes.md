### Next steps

1.  We aren't using versions:display-dependency-updates anymore. Therefore,
    we need to apply the rules.xml regex patterns ourselves in maven.py to
    filter out unwanted versions. Should be straightforward to do in Python.

2.  Do we need the history of the status table? I don't think we do.
    So then status.scijava.org should NO LONGER be a GitHub Pages site,
    but rather just this Python code, plus assets in an assets folder.
    All on the main branch, no more gh-pages branch.

    Then balinese can run this code as a cron job, and write the
    output site to the docroot at /var/www/status.scijava.org/

3.  Sanity check that the datestamp on the discovered SNAPSHOT.pom is very
    close to the <latest> value -- e.g., for legacy-imglib1, from maven-metadata.xml:

        <lastUpdated>20210702145659</lastUpdated>

    And on the file system:

        /opt/sonatype-work/nexus/storage/snapshots/sc/fiji/legacy-imglib1/1.1.10-SNAPSHOT/legacy-imglib1-1.1.10-20210702.145658-9.pom

    Note that these timestamps are off by 1 second. But close enough!

4.  Consider reintroducing a step that calls
    `mvn versions:display-dependency-updates` like newest-releases.sh used to do.

    Reasons to consider doing this, even though it is slow:
    -   Can apply rules.xml to filter newest versions to regex criteria.
    -   Might help keep maven.scijava.org proxies up-to-date with upstreams.
        But it doesn't invalidate the server-side caches for proxied
        artifacts; gotta do that too to be certain to have the latest.

5.  In the meantime: if the (3) sanity check fails, it means we don't have a
    POM we're confident is the best one. In that case, the HTML table should
    show question mark symbols in the columns normally pulled from the POM.

6.  Under what circumstances would we want to trigger an immediate rebuild of
    status.scijava.org? Ideally whenever pom-scijava changes. But also every
    hour. Or 30 minutes? or 10 minutes? Releases happen asynchronously!
    Probably just running it via cron every 30 minutes is good enough.
    But it would be great to have instant updates after a pom-scijava push.

### Heuristics

Things that affect how to interpret an issue:

if issue or PR is unscheduled:
* `issue['milestone']['title'] == 'unscheduled'`

if it's a PR; if it's a draft PR:
* `'pull_request' in issue`
* `'draft' in issue and issue['draft']`

when it was created, and when it was last updated:
* `issue['created_at']`
* `issue['updated_at']`

who is assigned: (do not use 'assignee'; 'assignees' is more general)
* `[assignee['login'] for assignee in issue['assignees']]`

if issue or PR has the question label: (i.e. waiting for feedback from someone else)
* `labels = [label['name'] for label in issue['labels']]`
* `'question' in labels`

number of comments?
* `issue['comments']`

if it's a bug versus an enhancement:
* `labels = [label['name'] for label in issue['labels']]`
* `'bug' in labels`
* `'enhancement' in labels`

### Red flags

```python
error = release_error = snapshot_error = pom_error = ""
error_prefix = "[ERROR] "
error_highlight = "--> "
if c.release is None:
    error = error_prefix
    release_error = error_highlight
if g in our_groups and c.snapshot is None:
    if c.snapshot is None:
        error = error_prefix
        snapshot_error = error_highlight
    if c.pom is not None and not c.pom.version.endswith('-SNAPSHOT'):
        error = error_prefix
        pom_error = error_highlight
if c.pom is None:
    error = error_prefix
    pom_error = error_highlight
print(f"\t{error}{g}:{a}")
print(f"\t\t{release_error}release = {c.release.source if c.release else None}")
print(f"\t\t{snapshot_error}snapshot = {c.snapshot.source if c.snapshot else None}")
print(f"\t\t{pom_error}pom = {c.pom.source if c.pom else None}")
```
