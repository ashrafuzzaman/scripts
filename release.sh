#!/bin/bash
cp src/git/gitconfig ~/.gitconfig

rm -rf out/*
npm install
npm run build
npm link

sudo ln -s src/bash/connect-bluetooth /usr/bin/
sudo ln -s src/bash/disconnect-bluetooth /usr/bin/
