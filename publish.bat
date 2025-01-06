@ECHO off

:: script for publishing files to Github repository (test)

git add .
git commit -am "file change"
git push origin main
