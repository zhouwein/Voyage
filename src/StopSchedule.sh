#!/bin/bash

kill -9 `ps -aux | grep -v grep |grep  "scheduler.py" |awk '{ print $2 }'`
kill -9 `ps -aux | grep -v grep |grep  "warc_queue.py" |awk '{ print $2 }'`
kill -9 `ps -aux | grep -v grep |grep  "wpull" |awk '{ print $2 }'`
kill -9 `ps -aux | grep -v grep |grep  "phantomjs" |awk '{ print $2 }'`