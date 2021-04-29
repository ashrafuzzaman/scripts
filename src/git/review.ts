import { SimpleGit } from 'simple-git';
import { withArgs, warn, info, hasUnstashedChanges, addRemote } from './utils';

const ARG_PATTERN = /(?<remote>.+)\:(?<branch>.+)?/i;

async function run() {
  withArgs(ARG_PATTERN, async (git: SimpleGit, { remote, branch }) => {
    if (!remote || !branch) return;

    if (await hasUnstashedChanges(git)) {
      return warn('Please stash your current changes');
    }

    await addRemote(git, remote);

    info(`Fetching changes from ${remote}/${branch}`);
    await git.fetch(remote, branch);

    if (await doesBranchExists(git, branch)) {
      warn('Reseting branch ...');
      await git.checkout(branch);
      await git.reset(['--hard', `${remote}/${branch}`]);
    } else {
      info(`Checking out branch: ${branch}`);
      await git.checkout(['-t', `${remote}/${branch}`]);
    }
  });
};

async function doesBranchExists(git, branch) {
  const branches = (await git.branchLocal()).all;
  return branches.some(_branch => _branch === branch);
}

run();
