@ECHO off

:: Script for resetting local repository to match fresh GitHub repository

:: Remove the old git repository
rmdir /s /q .git

:: Initialize a new repository
git init

:: Add the remote origin (replace with your GitHub repository URL)
git remote add origin https://github.com/m-jim-d/pet-code.git

:: Add all files
git add .

:: Make initial commit
git commit -m "Python 3 update: Removed PodSixNet dependency; New features for the drone puck and the jello simulations; Updated syntax for Python 3 compatibility."

:: Set the main branch (GitHub now uses 'main' instead of 'master')
git branch -M main

:: Push to the new repository
git push -u origin main
