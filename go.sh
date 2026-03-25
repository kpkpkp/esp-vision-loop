#!/bin/bash
cd ~/esp-vision-loop
git config --global user.email "kpkpkp@gmail.com"
git config --global user.name "kpkpkp"
git add -A
git commit -m "Initial commit: autonomous ESP32 code-see-judge-improve loop"
gh repo create esp-vision-loop --private --source=. --remote=origin --push
