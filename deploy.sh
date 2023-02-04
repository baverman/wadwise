#!/bin/sh
tar -cf - -T pack.list | ssh "$@" 'tar -C wadwise -xvf-'
