#!/usr/bin/env python
import sys
import pytest

if __name__ == "__main__":
    test_dir = __file__.replace('run_tests.py', '')
    sys.exit(pytest.main([test_dir, '-v', '--tb=short']))
