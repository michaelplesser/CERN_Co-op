function pathadd() {
  # TODO add check for empty path
  # and what happens if $1 == $2
  # Copy into temp variables
  PATH_NAME=$1
  PATH_VAL=${!1}
  if [[ ":$PATH_VAL:" != *":$2:"* ]]; then
    PATH_VAL="$2${PATH_VAL:+":$PATH_VAL"}"
    echo "- $1 += $2"

    # use eval to reset the target
    eval "$PATH_NAME=$PATH_VAL"
  fi

}

VICE_SW_TOP=$( readlink -f $(dirname $BASH_SOURCE)/ )

# add to path
pathadd PATH "${VICE_SW_TOP}/scripts"
pathadd PYTHONPATH "${VICE_SW_TOP}/utilities"

export PATH PYTHONPATH

