#!/bin/sh
#
# This is free and unencumbered software released into the public domain.
# See the UNLICENSE file for details.
#
# ------------------------------------------------------------------------
# update-website.sh
# ------------------------------------------------------------------------
# Regenerates the HTML content and pushes it to the gh-pages branch.

./html-report.sh > index-new.html &&
git fetch &&
git checkout gh-pages &&
git merge --ff --ff-only 'HEAD@{u}' &&
mv -f index-new.html index.html &&
git add index.html &&
git commit -m 'Update component table' &&
git push
