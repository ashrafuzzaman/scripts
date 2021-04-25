import { SimpleGit } from 'simple-git';
import { withArgs, warn, info } from './utils';
import * as readline from 'readline';

const ARG_PATTERN = /(?<remote>.+)\:(?<branch>.+)?/i;

async function run() {
  withArgs(ARG_PATTERN, async (git: SimpleGit, { remote, branch }) => {
    const status = await git.status();
    if (status.modified.length > 0) {
      return warn('Please stash your current changes');
    }

    await addRemote(git, remote);

    info(`Fetching changes from ${remote}/${branch}`);
    await git.fetch(remote, branch);

    if (await doesBranchExists(git, branch)) {
      const cliInterface = readline.createInterface({
        input: process.stdin,
        output: process.stdout
      })

      cliInterface.question(`Branch exists. Do you want to reset branch(${branch}) n/Y? `, async answer => {
        cliInterface.close();
        if (answer === 'Y') {
          warn('Reseting branch ...');
          await git.checkout(branch);
          await git.reset(['--hard', `${remote}/${branch}`]);
        } else {
          info('Skiping to reset branch.');
        }
      });
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

function remoteExists(remotes, remoteUrl) {
  return remotes.some(remote => remote.refs.fetch === remoteUrl);
}

async function addRemote(git, remote) {
  const remotes = await git.getRemotes(true);
  const gitRepoUrl = remotes[0].refs.fetch;
  const gitUrlPattern = /git@github.com:(?<remote>.+)\/(?<repoName>.+)\.git/i;
  const { repoName } = gitRepoUrl.match(gitUrlPattern).groups;
  const remoteUrl = `git@github.com:${remote}/${repoName}.git`;

  if (!remoteExists(remotes, remoteUrl)) {
    info(`Adding remote ${remote}`);
    await git.addRemote(remote, remoteUrl);
  }
}

run();
