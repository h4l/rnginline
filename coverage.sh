# Combine coverage of Python 2 and Python 3 runs to catch 2/3 specific code
set -e
echo "Combining coverage of Python 2 and 3 test runs:"
echo "==============================================="
coverage erase
tox -e py27,py34
coverage combine
coverage html
coverage report
