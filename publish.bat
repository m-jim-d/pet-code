@ECHO off

:: Script for publishing (deploying) files to Github repository 

git add .
git commit -am "file change"
git push origin main
