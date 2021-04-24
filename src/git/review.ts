import { SimpleGit } from 'simple-git';
import { getGit } from './utils';

export function run(): SimpleGit {
  const git: SimpleGit = getGit();
  const branches = git.branchLocal();
  console.log(branches);
  return git;
};

run();
