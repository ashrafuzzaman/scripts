#!/usr/bin/env python

from git import Repo
from utils import get_repo, get_or_create_remote, validate_author_branch, get_remote_tracking_branch


def rebase():
    repo = get_repo()

    if repo.is_dirty():
        print('The current branch has unstash changes')
        return

    print('Pulling changes from master')
    repo.remote('newscred').fetch('master')

    if repo.is_dirty():
        print('Please fix the rebase')
        return
    repo.git.rebase('newscred/master')
    print('Rebased to master')

    tracking_remote = get_remote_tracking_branch(repo)
    branch_name = repo.active_branch.name

    print('Force pusing to %s/%s' % (tracking_remote, branch_name))
    repo.git.push(tracking_remote, branch_name, force=True)


rebase()
