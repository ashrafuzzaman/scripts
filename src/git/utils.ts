import simpleGit, { SimpleGit, SimpleGitOptions } from 'simple-git';
import { parseArgument } from './argparser';

export function getGit(): SimpleGit {
  const options: Partial<SimpleGitOptions> = {
    baseDir: process.cwd(),
    binary: 'git'
  };

  return simpleGit(options);
};

export function withArgs(pattern: RegExp, next: Function) {
  const git: SimpleGit = getGit();
  next(git, parseArgument(pattern));
}
