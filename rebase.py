#!/usr/bin/env python

from git import Repo, GitCommandError
from utils import get_repo, get_or_create_remote, validate_author_branch


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
    # TODO: Push to remote branch
    # repo.git.push()


rebase()
