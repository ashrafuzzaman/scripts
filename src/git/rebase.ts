import { SimpleGit } from 'simple-git';
import { getGit, warn, info, hasUnstashedChanges, addRemote } from './utils';

async function run() {
  const git: SimpleGit = getGit();
  const REBASE_REMOTE = 'newscred';
  const REBASE_BRANCH = 'master';

  if (await hasUnstashedChanges(git)) {
    return warn('Please stash your current changes');
  }

  await addRemote(git, REBASE_REMOTE);

  info(`Fetching changes from ${REBASE_REMOTE}/${REBASE_BRANCH}`);
  await git.fetch(REBASE_REMOTE, REBASE_BRANCH);

  info('Rebasing ...');
  await git.rebase([`${REBASE_REMOTE}/${REBASE_BRANCH}`]);
};

run();
