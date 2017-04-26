#!/bin/sh

# update-website.sh

# Regenerates the HTML content and pushes it to the gh-pages branch.

./html-report.sh > index-new.html &&
git checkout gh-pages &&
mv -f index-new.html index.html &&
git add index.html &&
git commit -m 'Update component table' &&
git push
