#!/bin/bash

[ -f ~/.gitconfig ] || cp src/git/config/gitconfig ~/.gitconfig
touch ~/.gitignore

[ -f ~/.newscred.yaml ] || cp src/bash/config/newscred.yaml ~/.newscred.yaml

rm -rf out/*
npm install
npm run build
npm link

base_path=$(pwd)
sudo rm -rf /usr/bin/connect-bluetooth && sudo ln -s "$base_path/src/bash/connect-bluetooth" /usr/bin/
sudo rm -rf /usr/bin/disconnect-bluetooth && sudo ln -s "$base_path/src/bash/disconnect-bluetooth" /usr/bin/
sudo rm -rf /usr/bin/pull-containers && sudo ln -s "$base_path/src/bash/pull-containers" /usr/bin/
sudo rm -rf /usr/bin/update-containers && sudo ln -s "$base_path/src/bash/update-containers" /usr/bin/
sudo rm -rf /usr/bin/fix-camlink && sudo ln -s "$base_path/src/bash/fix-camlink" /usr/bin/
