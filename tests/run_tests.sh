#!/bin/bash

python3 tests/shell_test.py

if [[ $? -ne 0 ]]; then
  exit 1
fi