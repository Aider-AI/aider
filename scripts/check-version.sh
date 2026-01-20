#!/usr/bin/env sh
version=$(python -m setuptools_scm)
# Check if the version is pure (i.e., it doesn't contain a '+')
echo "$version" | grep -q "+" && {
  echo "Error: Version '$version' is not pure. Aborting dist."
  exit 1
}
exit 0
