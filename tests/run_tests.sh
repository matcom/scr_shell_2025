#!/bin/bash

python3 tests/main.py

if [[ $? -ne 0 ]]; then
  exit 1
fi