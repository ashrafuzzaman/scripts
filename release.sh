#!/bin/bash
cp src/git/gitconfig ~/.gitconfig

rm -rf out/*
npm run build
npm link
