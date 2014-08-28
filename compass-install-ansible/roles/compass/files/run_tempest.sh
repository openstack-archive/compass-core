#!/bin/bash

cd /tmp/tempest
git reset --hard
git clean -x -f -d -q
git checkout grizzly-eol
