#!/bin/sh
tar -chf - -T pack.list | ssh "$@" 'tar -C wadwise -xvf-'
