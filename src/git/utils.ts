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
  console.info('Current directory: ', process.cwd());
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
