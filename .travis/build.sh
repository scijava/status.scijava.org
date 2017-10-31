#!/bin/sh

# Regenerate the HTML content.
./html-report.sh > index-new.html &&

# Push it to the gh-pages branch.
git clone --depth=1 --branch=gh-pages https://github.com/scijava/status.scijava.org site &&
mv -f index-new.html site/index.html &&
cd site &&
git remote set-url origin --push git@github.com:scijava/status.scijava.org &&
if [ "$TRAVIS_BUILD_NUMBER" ]
then
  commitNote="Travis build $TRAVIS_BUILD_NUMBER"
else
  commitNote=$(date)
fi &&
git commit -m "Update component table ($commitNote)" index.html &&
git push
