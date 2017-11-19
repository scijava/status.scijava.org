#!/bin/sh

# Regenerate the HTML content.
./html-report.sh > index-new.html &&

# Push it to the gh-pages branch.
git clone --depth=1 --branch=gh-pages git@github.com:scijava/status.scijava.org site &&
mv -f index-new.html site/index.html &&
cd site &&
if [ "$TRAVIS_BUILD_NUMBER" ]
then
  commitNote="Travis build $TRAVIS_BUILD_NUMBER"
else
  commitNote=$(date)
fi &&
if git diff --quiet index.html
then
  echo "== No new changes =="
else
  echo "== Pushing changes =="
  git commit -m "Update component table ($commitNote)" index.html &&
  git push
fi
