import { SimpleGit } from 'simple-git';
import { getGit, warn, info, hasUnstashedChanges } from './utils';

async function run() {
  const git: SimpleGit = getGit();
  const status = await git.status();

  if (await hasUnstashedChanges(git)) {
    return warn('Please stash your current changes');
  }


  if (status.tracking) {
    info(`Pusing to ${status.tracking}`);
    const [remote, branch] = status.tracking.split('/');
    await git.push(remote, branch, ['-f']);
  }
};

run();
