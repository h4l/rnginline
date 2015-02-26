# Combine coverage of Python 2 and Python 3 runs to catch 2/3 specific code
set -e
cd "$( dirname "${BASH_SOURCE[0]}" )"

echo "Combining coverage of Python 2 and 3 test runs:"
echo "==============================================="

coverage erase
# the coverage_combined factor uses the -p coverage run switch to save coverage
# from different runs in different coverage files.
tox -e "{py27,py34}-coverage_combined"
coverage combine
coverage html

echo
echo "Combined coverage of Python 2 and 3 test runs:"
echo "=============================================="
echo
coverage report
