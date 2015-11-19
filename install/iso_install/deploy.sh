#set -x
COMPASS_DIR=`cd ${BASH_SOURCE[0]%/*}/;pwd`
export COMPASS_DIR

for i in python-cheetah python-yaml screen; do
    if [[ `dpkg-query -l $i` == 0 ]]; then
        continue
    fi
    sudo apt-get install -y --force-yes  $i
done

screen -ls |grep deploy|awk -F. '{print $1}'|xargs kill -9
screen -wipe
#screen -dmSL deploy bash $COMPASS_DIR/ci/launch.sh $*
$COMPASS_DIR/deploy/launch.sh $*
