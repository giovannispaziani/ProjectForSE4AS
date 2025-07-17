@echo off
set PWD=%CD%

echo Copying utils to relevant components...

xcopy utils\* analyzer\utils\ /E /Y /I
xcopy utils\* monitor\sensors\utils\ /E /Y /I
xcopy utils\* planner\utils\ /E /Y /I
xcopy utils\* executors\utils\ /E /Y /I
xcopy utils\* executors\actuators\utils\ /E /Y /I

echo Starting Docker Compose...
docker compose up

echo Cleaning up copied utils folders...

rd /S /Q analyzer\utils
rd /S /Q monitor\sensors\utils
rd /S /Q planner\utils
rd /S /Q executors\utils
rd /S /Q executors\actuators\utils

docker compose down

echo Done.
