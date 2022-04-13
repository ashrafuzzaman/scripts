#!/bin/bash
cp src/git/gitconfig ~/.gitconfig

rm -rf out/*
npm install
npm run build
npm link
