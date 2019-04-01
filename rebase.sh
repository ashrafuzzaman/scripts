#!/bin/bash

branch_name="$(git symbolic-ref --short -q HEAD)"
echo "Rebasing" $branch_name
git fetch newscred master:master && git rebase newscred/master && git push --force origin $branch_name
