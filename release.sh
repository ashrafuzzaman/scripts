#!/bin/bash

rm -rf out/*
npm install
npm run build
npm link
