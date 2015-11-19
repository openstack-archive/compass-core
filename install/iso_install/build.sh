#!/bin/bash
set -ex

SCRIPT_DIR=`cd ${BASH_SOURCE[0]%/*};pwd`
COMPASS_DIR=${SCRIPT_DIR}
WORK_DIR=$SCRIPT_DIR/work/building
PACKAGES="fuse fuseiso createrepo genisoimage curl"

source $SCRIPT_DIR/build/build.conf

mkdir -p $WORK_DIR

cd $WORK_DIR
function prepare_env()
{
    set +e
    for i in $PACKAGES; do
        if ! apt --installed list 2>/dev/null |grep "\<$i\>"
        then
            sudo apt-get install  -y --force-yes  $i
        fi
    done
    set -e

    if [[ ! -d $CACHE_DIR ]]; then
        mkdir -p $CACHE_DIR
    fi
}

function download_git()
{
    file_dir=$CACHE_DIR/${1%.*}
    if [[ -d $file_dir/.git ]]; then
        cd $file_dir
        git pull origin master
        cd -
    else
        rm -rf $CACHE_DIR/$file_dir
        git clone $2 $file_dir
    fi
}

function download_url()
{
    rm -f $CACHE_DIR/$1.md5
    curl --connect-timeout 10 -o $CACHE_DIR/$1.md5 $2.md5 2>/dev/null
    if [[ -f $CACHE_DIR/$1 ]]; then
        local_md5=`md5sum $CACHE_DIR/$1 | cut -d ' ' -f 1`
        repo_md5=`cat $CACHE_DIR/$1.md5 | cut -d ' ' -f 1`
        if [[ $local_md5 == $repo_md5 ]]; then
            return
        fi
    fi

    curl --connect-timeout 10 -o $CACHE_DIR/$1 $2
}

function download_local()
{
    if [[ $2 != $CACHE_DIR/$1 ]]; then
       cp $2 $CACHE_DIR/ -rf
    fi
}

function download_packages()
{
     for i in $CENTOS_BASE $COMPASS_CORE $COMPASS_WEB $COMPASS_INSTALL $TRUSTY_JUNO_PPA $UBUNTU_ISO \
              $CENTOS_ISO $CENTOS7_JUNO_PPA $CENTOS7_KILO_PPA $LOADERS $CIRROS $APP_PACKAGE $COMPASS_PKG \
              $PIP_REPO $ANSIBLE_MODULE; do

         if [[ ! $i ]]; then
             continue
         fi
         name=`basename $i`

         if [[ ${name##*.} == git ]]; then
             download_git  $name $i
         elif [[ "https?" =~ ${i%%:*} || "file://" =~ ${i%%:*} ]]; then
             download_url  $name $i
         else
             download_local $name $i
         fi
     done

}

function copy_file()
{
    new=$1

    # main process
    mkdir -p $new/compass $new/bootstrap $new/pip $new/guestimg $new/app_packages $new/ansible
    mkdir -p $new/repos/cobbler/{ubuntu,centos}/{iso,ppa}

    cp -rf $SCRIPT_DIR/util/ks.cfg $new/isolinux/ks.cfg

    rm -rf $new/.rr_moved

    if [[ $UBUNTU_ISO ]]; then
        cp $CACHE_DIR/`basename $UBUNTU_ISO` $new/repos/cobbler/ubuntu/iso/ -rf
    fi

    if [[  $TRUSTY_JUNO_PPA ]]; then
        cp $CACHE_DIR/`basename $TRUSTY_JUNO_PPA` $new/repos/cobbler/ubuntu/ppa/ -rf
    fi

    if [[ $CENTOS_ISO ]]; then
        cp $CACHE_DIR/`basename $CENTOS_ISO` $new/repos/cobbler/centos/iso/ -rf
    fi

    if [[ $CENTOS7_JUNO_PPA ]]; then
        cp $CACHE_DIR/`basename $CENTOS7_JUNO_PPA` $new/repos/cobbler/centos/ppa/ -rf
    fi

    if [[ $CENTOS7_KILO_PPA ]]; then
        cp $CACHE_DIR/`basename $CENTOS7_KILO_PPA` $new/repos/cobbler/centos/ppa/ -rf
    fi

    cp $CACHE_DIR/`basename $LOADERS` $new/ -rf || exit 1
    cp $CACHE_DIR/`basename $APP_PACKAGE` $new/app_packages/ -rf || exit 1
    cp $CACHE_DIR/`basename $ANSIBLE_MODULE | sed 's/.git//g'`  $new/ansible/ -rf || exit 1

    if [[ $CIRROS ]]; then
        cp $CACHE_DIR/`basename $CIRROS` $new/guestimg/ -rf || exit 1
    fi

    for i in $COMPASS_CORE $COMPASS_INSTALL $COMPASS_WEB; do
        cp $CACHE_DIR/`basename $i | sed 's/.git//g'` $new/compass/ -rf
    done

    cp $COMPASS_DIR/deploy/adapters $new/compass/compass-adapters -rf

    tar -zxvf $CACHE_DIR/`basename $PIP_REPO` -C $new/

    find $new/compass -name ".git" | xargs rm -rf
}

function rebuild_ppa()
{
    name=`basename $COMPASS_PKG`
    rm -rf ${name%%.*} $name
    cp $CACHE_DIR/$name $WORK_DIR
    cp $SCRIPT_DIR/build/os/centos/comps.xml $WORK_DIR
    tar -zxvf $name
    cp ${name%%.*}/*.rpm $1/Packages -f
    rm -rf $1/repodata/*
    createrepo -g $WORK_DIR/comps.xml $1
}

function make_iso()
{
    download_packages
    name=`basename $CENTOS_BASE`
    cp  $CACHE_DIR/$name ./ -f
    # mount base iso
    mkdir -p base new
    fuseiso $name base
    cd base;find .|cpio -pd ../new ;cd -
    fusermount -u base
    chmod 755 ./new -R

    copy_file new
    rebuild_ppa new

    mkisofs -quiet -r -J -R -b isolinux/isolinux.bin \
            -no-emul-boot -boot-load-size 4 \
            -boot-info-table -hide-rr-moved \
            -x "lost+found:" \
            -o compass.iso new/

    md5sum compass.iso > compass.iso.md5

    # delete tmp file
    rm -rf new base $name
}

function process_param()
{
    TEMP=`getopt -o c:d:f: --long iso-dir:,iso-name:,cache-dir: -n 'build.sh' -- "$@"`

    if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

    eval set -- "$TEMP"

    while :; do
        case "$1" in
            -d|--iso-dir) export ISO_DIR=$2; shift 2;;
            -f|--iso-name) export ISO_NAME=$2; shift 2;;
            -c|--cache-dir) export CACHE_DIR=$2; shift 2;;
            --) shift; break;;
            *) echo "Internal error!" ; exit 1 ;;
        esac
    done

    export CACHE_DIR=${CACHE_DIR:-$WORK_DIR/cache}
    export ISO_DIR=${ISO_DIR:-$WORK_DIR}
    export ISO_NAME=${ISO_NAME:-"compass.iso"}
}

function copy_iso()
{
   if [[ $ISO_DIR/$ISO_NAME == $WORK_DIR/compass.iso ]]; then
      return
   fi

   cp $WORK_DIR/compass.iso $ISO_DIR/$ISO_NAME -f
}

process_param $*
prepare_env
make_iso
copy_iso
