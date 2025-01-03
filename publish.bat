@ECHO off

:: Script for publishing (deploying) files to Github repository 

git add .
git commit -am "Python 3 update: Removed PodSixNet dependency; New features for the drone puck and the jello simulations; Updated syntax for Python 3 compatibility."
git push origin main
