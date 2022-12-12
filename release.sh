#!/bin/bash

[ -f ~/.newscred.yaml ] || cp src/bash/config/newscred.yaml ~/.newscred.yaml
[ -f ~/.bash_aliases ] || cp src/bash/config/bash_aliases ~/.bash_aliases

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
