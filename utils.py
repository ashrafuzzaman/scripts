#!/usr/bin/env python

import os
import argparse
from git import Repo


def get_repo():
    return Repo(os.getcwd())


def get_or_create_remote(repo, author):
    try:
        return repo.remote(author)
    except:
        print('Adding %s as new remote', author)
        git_url = repo.remote('newscred').urls.next()
        return repo.create_remote(author, url=git_url.replace('newscred', author))


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
