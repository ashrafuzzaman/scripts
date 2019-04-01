#!/bin/bash

IFS=':' read -r -a input_str <<< $1

remote=$input_str[0]
branch=$input_str[1]
echo "${remote}:${branch}"

# branch_name="$(git symbolic-ref --short -q HEAD)"
# echo "Rebasing" $branch_name
# git fetch newscred master:master && git rebase newscred/master && git push --force origin $branch_name
