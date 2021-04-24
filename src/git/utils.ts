import simpleGit, { SimpleGit, SimpleGitOptions } from 'simple-git';

export function getGit(): SimpleGit {
  const options: Partial<SimpleGitOptions> = {
    baseDir: process.cwd(),
    binary: 'git'
  };

  return simpleGit(options);
};

