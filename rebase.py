#!/usr/bin/env python

from git import Repo, GitCommandError
from utils import get_repo, get_or_create_remote, validate_author_branch


def rebase():
    repo = get_repo()

    if repo.is_dirty():
        print('The current branch has unstash changes')
        return

    print('Pulling changes from master')
    import ipdb
    ipdb.set_trace()
    repo.remote('newscred').fetch('master')
    repo.git.rebase('newscred/master')

    if repo.is_dirty():
        print('Please fix the rebase')
        return
    repo.git.rebase('newscred/master')
    # TODO: Push to remote branch


rebase()
