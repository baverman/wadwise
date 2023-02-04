#!/bin/bash
mkdir -p $HOME/shared/wadwise
export WADWISE_DB=$HOME/shared/wadwise/data.sqlite
exec python $(dirname $0)/main.py
