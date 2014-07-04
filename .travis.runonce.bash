#!/usr/bin/env bash
# This script does the things that we want Travis to do only once, not in 
# every possible build.

# Set environment
# Which branch are we on?
branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')

# Check translations
sandbox/check_trans.py plugins/
sandbox/check_trans.py --core

# Do these things only on testing or master.
if [[ "$branch" = "master" || "$branch" = "testing" ]]; then
    # Notify read the docs
    curl -X POST http://readthedocs.org/build/limnoria
    # Add other things which we want to do here, before the fi.
else
    echo "$branch is not master nor testing, doing nothing."
fi
