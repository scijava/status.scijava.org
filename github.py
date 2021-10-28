#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# github.py
# ------------------------------------------------------------------------
# A class to download and organize information from GitHub.

import datetime, json, logging, math, sys, time
import requests

class GitHubIssue:

    def __init__(self, data):
        self._data = data

    @staticmethod
    def _datetime(timestamp):
        # Credit: https://stackoverflow.com/a/969324/1207769
        return datetime.datetime.strptime('2019-01-04T16:41:24+0200', "%Y-%m-%dT%H:%M:%S%z")

    @property
    def created_at(self):
        return GitHubIssue._datetime(self._data['created_at'])

    @property
    def updated_at(self):
        return GitHubIssue._datetime(self._data['updated_at'])

    @property
    def is_pr(self):
        return 'pull_request' in self._data

    @property
    def is_draft(self):
        return 'draft' in self._data

    @property
    def milestone(self):
        return self._data['milestone']['title'] if self._data['milestone'] else None

    @property
    def labels(self):
        return [label['name'] for label in self._data['labels']]

    @property
    def assignees(self):
        return [assignee['login'] for assignee in self._data['assignees']]

class GitHubIssues:

    def __init__(self, items=[], token=None):
        self._token = token
        self._items = items
        self._delay_per_request = 5
        self._max_requests = 100

    def repo(self, org, repo):
        """
        Filter the collection of issues to only those in the given repository.
        """
        return GitHubIssues([item for item in self._items if item['repository_url'].endswith(f'/repos/{org}/{repo}')], token=self._token)

    def issues(self):
        """
        Return the collection of issues as a list of GitHubIssue objects.
        """
        return list(map(GitHubIssue, self._items))

    def load(self, filepath):
        """
        Load issues from the given JSON file.
        """
        with open(filepath) as f:
            result = json.loads(f.read())
            self._items.extend(result)

    def save(self, filepath):
        """
        Save issues to the given JSON file.
        """
        with open(filepath, 'w') as f:
            return json.dump(self._items, f, sort_keys=True, indent=4)

    @staticmethod
    def _search_url(query):
        return f"https://api.github.com/search/issues?q={query}+is:open&sort=created&order=asc&per_page=100"

    def download(self, query):
        """
        Download issues from GitHub according to the given query.
        """
        url = GitHubIssues._search_url(query)
        for _ in range(self._max_requests):
            url = self._download_page(url, query)
            if not url: break
            time.sleep(self._delay_per_request)

    def _download_page(self, url, query):
        headers = {'User-Agent': 'status.scijava.org'}
        if self._token: headers['Authorization'] = "token " + self._token

        logging.debug(f'Downloading {url}')
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        self._items.extend(result['items'])

        next_url = response.links['next']['url'] if 'next' in response.links else None
        if not next_url and result['total_count'] > 1000 and len(result['items']) > 0:
            # We hit the 1000-issue limit. Continue the search just beyond the last issue we got.
            next_url = GitHubIssues._search_url(f"{query}+created:>{result['items'][-1]['created_at']}")
        return next_url

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: github.py <query>")
        print("Ex: github.py repo:scijava/pom-scijava")
        sys.exit(1)
    query = "+".join(sys.argv[1:])
    ghi = GitHubIssues()
    ghi.download(query)
    print(json.dumps(ghi._json, sort_keys=True, indent=4))
