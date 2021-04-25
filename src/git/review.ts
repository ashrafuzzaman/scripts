import { SimpleGit } from 'simple-git';
import { withArgs, warn, info } from './utils';

const ARG_PATTERN = /(?<remote>.+)\:(?<branch>.+)?/i;

async function run() {
  withArgs(ARG_PATTERN, async (git: SimpleGit, { remote, branch }) => {
    const status = await git.status();
    if (status.modified.length > 0) {
      return warn('Please stash your current changes');
    }

    await addRemote(git, remote);
    // await git.fetch(remote, branch);
  });
};

async function remoteExists(remotes, remoteUrl) {
  console.log(remotes);
  const exists = remotes.some(remote => remote.refs.fetch === remoteUrl);
  console.log('exists: ', exists)
  return exists;
}

async function addRemote(git, remote) {
  const remotes = await git.getRemotes(true);
  const gitRepoUrl = remotes[0].refs.fetch;
  const gitUrlPattern = /git@github.com:(?<remote>.+)\/(?<repoName>.+)\.git/i;
  const { repoName } = gitRepoUrl.match(gitUrlPattern).groups;
  const remoteUrl = `git@github.com:${remote}/${repoName}.git`;

  console.log('remoteUrl: ', remoteUrl);
  
  if (!remoteExists(remotes, remoteUrl)) {
    info(`Adding remote ${remote}`);
    await git.addRemote(remote, remoteUrl);
  }
}

run();
