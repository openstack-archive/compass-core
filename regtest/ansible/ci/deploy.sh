SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source ${SCRIPT_DIR}/prepare.sh || exit $?
source ${SCRIPT_DIR}/setup-env.sh || exit $?
source ${SCRIPT_DIR}/deploy-vm.sh || exit $?
