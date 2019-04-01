#!/usr/bin/env python

import os
import argparse
from git import Repo
from utils import get_repo, get_or_create_remote, validate_author_branch


def review(author, branch):
    repo = get_repo()

    if repo.is_dirty():
        print('The current branch has unstash changes')
        return

    remote = get_or_create_remote(repo, author)

    print('Fetching for new changes')
    remote.fetch(branch)
    
    print('Checkout to %s' % branch)
    if not branch in repo.branches:
        repo.git.checkout('-t', '%s/%s' % (author, branch))
    else:
        repo.git.checkout(branch)
        repo.git.reset('--hard', '%s/%s' % (author, branch))


def run():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('author_branch',
                        type=validate_author_branch,
                        help='<github_author>:<branch_name>')
    args = parser.parse_args()
    review(args.author_branch['author'], args.author_branch['branch'])


run()
