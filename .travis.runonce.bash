#!/usr/bin/env bash
# This script does the things that we want Travis to do only once, not in 
# every possible build.

# Care about exit status
set -x
set -e

# Set environment
# Which branch are we on?
branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')

# Install requirements required for only this file.
if [[ $TRAVIS == "true" ]]; then
    sudo pip install sphinx msgcheck --upgrade
else
    pip install sphinx msgcheck --upgrade --user
fi

# Check translations
sandbox/check_trans.py plugins/
sandbox/check_trans.py --core
msgcheck -flwWp plugins/*/*/*.po || true
msgcheck -flwWp locales/*.po || true

# Check documentation
cd docs
# Add -W to spinx-build when the documentation doesn't error!
sphinx-build -n -b html -d _build/doctrees . _build/html
cd ..
