#!/bin/bash

cd ~/projects/localdev/
git checkout master && git pull newscred master

pyenv activate localdev
nc-docker configure

cd ~/projects
nc-docker update

(
  for repo in cmp-client cmp-server assets sso; do
    echo "Building $repo"
    nc-docker build $repo
  done
)
