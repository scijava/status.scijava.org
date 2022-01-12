#!/bin/sh

# Regenerate the HTML content.
python html-report.py > index-new.html &&

# Push it to the gh-pages branch.
git clone --depth=1 --branch=gh-pages git@github.com:scijava/status.scijava.org site &&
mv -f index-new.html site/index.html &&
git config --global user.name github-actions &&
git config --global user.email github-actions@github.com &&
cd site &&
if git diff --quiet index.html
then
  echo "== No new changes =="
else
  echo "== Pushing changes =="
  commitNote="$(TZ=UTC date +'%Y-%M-%d %H:%m:%S UTC')"
  git commit -m "Update component table ($commitNote)" index.html &&
  git push
fi
