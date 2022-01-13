#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# github.py
# ------------------------------------------------------------------------
# A class to download and organize information from GitHub.

import json, logging, sys, time
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

class GitHubIssue:

    def __init__(self, data):
        self._data = data

    @staticmethod
    def _datetime(timestamp: str) -> datetime:
        """
        :param timestamp: Timestamp in ISO 8601 format.
                          Ex: 2019-01-04T16:41:24+0200
        """
        # Credit: https://stackoverflow.com/a/969324/1207769
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")

    @property
    def created_at(self) -> datetime:
        return GitHubIssue._datetime(self._data['created_at'])

    @property
    def updated_at(self) -> datetime:
        return GitHubIssue._datetime(self._data['updated_at'])

    @property
    def is_pr(self) -> bool:
        return 'pull_request' in self._data

    @property
    def is_draft(self) -> bool:
        return 'draft' in self._data

    @property
    def milestone(self) -> str:
        return self._data['milestone']['title'] if self._data['milestone'] else None

    @property
    def labels(self) -> List[str]:
        return [label['name'] for label in self._data['labels']]

    @property
    def assignees(self) -> List[str]:
        return [assignee['login'] for assignee in self._data['assignees']]

class GitHubIssues:

    def __init__(self, items: List[Dict[str, Any]] = None, token: str = None):
        self._token = token
        self._items = [] if items is None else items
        self._delay_per_request = 5
        self._max_requests = 100

    def repo(self, org: str, repo: str) -> 'GitHubIssues':
        """
        Filter the collection of issues to only those in the given repository.
        """
        return GitHubIssues([item for item in self._items if str(item['repository_url']).endswith(f'/repos/{org}/{repo}')], token=self._token)

    def issues(self) -> List[GitHubIssue]:
        """
        Return the collection of issues as a list of GitHubIssue objects.
        """
        return list(map(GitHubIssue, self._items))

    def load(self, filepath: Union[str, Path]) -> None:
        """
        Load issues from the given JSON file.
        """
        with open(filepath) as f:
            result = json.loads(f.read())
            self._items.extend(result)

    def save(self, filepath: Union[str, Path]) -> None:
        """
        Save issues to the given JSON file.
        """
        with open(filepath, 'w') as f:
            json.dump(self._items, f, sort_keys=True, indent=4)

    def __str__(self) -> str:
        """
        Return issues as a JSON string.
        """
        return json.dumps(self._items, sort_keys=True, indent=4)

    @staticmethod
    def _search_url(query: str) -> str:
        return f"https://api.github.com/search/issues?q={query}+is:open&sort=created&order=asc&per_page=100"

    def download(self, query: str) -> None:
        """
        Download issues from GitHub according to the given query.
        """
        url = GitHubIssues._search_url(query)
        for _ in range(self._max_requests):
            url = self._download_page(url, query)
            if not url: break
            time.sleep(self._delay_per_request)

    def _download_page(self, url: str, query: str) -> str:
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

def main(args: Sequence[str]) -> None:
    if len(args) < 1:
        print("Usage: github.py <query>")
        print("Ex: github.py repo:scijava/pom-scijava")
        sys.exit(1)
    query = "+".join(args)
    ghi = GitHubIssues()
    ghi.download(query)
    print(ghi)

if __name__ == '__main__':
    main(sys.argv[1:])
