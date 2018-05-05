#!/bin/bash

export PYTHONPATH=/usr/local/lib/nemesis/python:$PYTHONPATH

for i in {1..3}
do
    for ff in AC CE FPE FSZ ILL MLE NON TLE SEG WA
    do
        python3 ./gen_job.py --lang CXX --out ./submit.nemesis --user_id 1 --task_id 1 --source ./src/${ff}.cpp
        python3 ./client.py --submit ./submit.nemesis --addr 172.20.0.9 --port 5555
        python3 ./gen_ci.py --out ci.nemesis --lang CXX --source ./src/${ff}.cpp --in ./1/1/in/1 --user_id 1
        python3 ./client.py --submit ./ci.nemesis --addr 172.20.0.9 --port 5555
    done
done
