import simpleGit, { SimpleGit, SimpleGitOptions } from 'simple-git';
const colors = require('colors/safe');

function parseArgument(pattern) {
  const args = process.argv[2];
  const match = args.match(pattern);
  if (!match) {
    warn(`Missing argument, ${pattern}`);
    return {};
  }
  return match.groups;
};

export function getGit(): SimpleGit {
  const options: Partial<SimpleGitOptions> = {
    baseDir: process.cwd(),
    binary: 'git'
  };

  return simpleGit(options);
};

export function withArgs(pattern: RegExp, next: (git: SimpleGit, params: Record<string, any>) => void) {
  const git: SimpleGit = getGit();
  next(git, parseArgument(pattern));
}

export function warn(text) {
  console.warn(colors.yellow(text));
}

export function info(text) {
  console.info(text);
}

export async function hasUnstashedChanges(git) {
  const status = await git.status();
  return status.modified.length > 0;
}

function remoteExists(remotes, remoteUrl) {
  return remotes.some(remote => remote.refs.fetch === remoteUrl);
}

export async function addRemote(git, remote) {
  const remotes = await git.getRemotes(true);
  const gitRepoUrl = remotes[0].refs.fetch;
  const gitUrlPattern = /git@github.com:(?<remote>.+)\/(?<repoName>.+)\.git/i;
  const { repoName } = gitRepoUrl.match(gitUrlPattern).groups;
  const remoteUrl = `git@github.com:${remote}/${repoName}.git`;

  if (!remoteExists(remotes, remoteUrl)) {
    info(`Adding remote ${remote}`);
    await git.addRemote(remote, remoteUrl);
  }
}
