#!/bin/bash

rm -rf out/*
npm run build
npm link
npm install -g .