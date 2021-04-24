import { SimpleGit } from 'simple-git';
import { withArgs } from './utils';

const ARG_PATTERN = /(?<remote>.+)\:(?<branch>.+)?/i;

async function run() {
  withArgs(ARG_PATTERN, async (git: SimpleGit, { remote, branch }) => {
    console.info(remote, branch);
    const branchSummery = await git.branchLocal();
    console.log('branches', branchSummery);
    return git;
  });
};

run();
