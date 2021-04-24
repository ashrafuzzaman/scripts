import { SimpleGit } from 'simple-git';
import { getGit } from './utils';
import { parseArgument } from './argparser';

function getRemoteAndBranch() {
  const pattern = /(?<remote>\w+)\:(?<branch>\w+)?/i;
  return parseArgument(pattern);
}

export async function run(): Promise<SimpleGit> {
  const { remote, branch } = getRemoteAndBranch();
  const git: SimpleGit = getGit();
  const branchSummery = await git.branchLocal();
  console.log('branches', branchSummery);
  return git;
};

run();
