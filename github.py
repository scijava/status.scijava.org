#!/usr/bin/env python
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# github.py
# ------------------------------------------------------------------------
# A class to download and organize information from GitHub.

import json, logging, math
import requests

class GitHubIssues:

    def __init__(self, items=[], max_results=10000, token=None):
        self._token = token
        self._json = {'items': items}
        self._per_page = 100
        self._max_results = max_results

    def repo(self, org, repo):
        return GitHubIssues(self.issues(lambda item: item['repository_url'].endswith(f'/repos/{org}/{repo}')),
                            max_results=self._max_results, token=self._token)

    def prs(self):
        return GitHubIssues(self.issues(lambda item: item['pull_request'] is True),
                            max_results=self._max_results, token=self._token)

    def issues(self, predicate=lambda x: True):
        return list(filter(predicate, self._json['items']))

    def load(self, filepath):
        with open(filepath) as f:
            result = json.loads(f.read())
            self._merge(result)

    def save(self, filepath):
        with open(filepath, 'w') as f:
            return json.dump(self._json, f)

    def download(self, query):
        """
        Downloads issues from GitHub according to the given query.
        """

        url = f"https://api.github.com/search/issues?q={query}+is:open&sort=created&order=asc&per_page={self._per_page}"
        url = self._download_page(url)

        max_pages = math.ceil(self._max_results / self._per_page)
        for i in range(1, max_pages):
            if not url: break
            url = self._download_page(url)

    def _download_page(self, url):
        headers = {}
        if self._token: headers['Authorization'] = self._token

        logging.debug(f'Downloading {url}')
        response = requests.get(url, headers)
        result = response.json()

        self._merge(result)

        return response.links['next']['url'] if 'next' in response.links else None

    def _merge(self, content):
        for key, value in content.items():
            if key in self._json and type(self._json[key]) == list:
                # Append values to the list.
                self._json[key].extend(value)
            else:
                # Overwrite value in the dict.
                self._json[key] = value
