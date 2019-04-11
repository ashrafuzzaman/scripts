#!/usr/bin/env python

import os
import argparse
from git import Repo
import re


def get_repo():
    return Repo(os.getcwd())


def get_or_create_remote(repo, author):
    try:
        return repo.remote(author)
    except:
        print('Adding %s as new remote', author)
        git_url = repo.remote('newscred').urls.next()
        return repo.create_remote(author, url=git_url.replace('newscred', author))


def get_remote_tracking_branch(repo):
    # Sample git branch -vv line
    # * fix-kinesis 15b23666ef [remote_tracking_name/branch] Commit message
    regex = re.compile(r'^\* .+\[(.+)\/')
    current_branches = filter(regex.match, repo.git.branch('-vv').split('\n'))

    if len(current_branches) > 0:
        return regex.match(current_branches[0]).group(1)
    return None


def validate_author_branch(input):
    try:
        author, branch = input.split(':')
        if not author or not branch:
            raise Exception()
        return {'author': author, 'branch': branch}
    except:
        msg = "Invalid format: '{0}'. Should be like <github_author>:<branch_name>".format(
            input)
        raise argparse.ArgumentTypeError(msg)
