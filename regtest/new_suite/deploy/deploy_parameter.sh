#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
set -x
function get_option_name_list()
{
    echo $(echo "$1" | xargs -n 1 grep -oP "export .*?=" | \
            awk '{print $2}' | sort | uniq | sed -e 's/=$//g')
}
function get_option_flag_list()
{
    echo $(echo "$1" | tr [:upper:] [:lower:] | \
                 xargs | sed  -e 's/ /:,/g' -e 's/_/-/g')
}

function get_conf_name()
{
    if [[ -n $DHA ]]; then
        return
    fi

    cfg_file=`ls $COMPASS_DIR/deploy/conf/*.conf`
    option_name=`get_option_name_list "$cfg_file"`
    option_flag=`get_option_flag_list "$option_name"`

    TEMP=`getopt -o h -l dha:,network:,neutron:,conf-dir:,$option_flag -n 'deploy_parameter.sh' -- "$@"`

    if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi
    eval set -- "$TEMP"
    while :; do
        if [[ "$1" == "--" ]]; then
            shift
            break
        fi
        shift
    done

    if [[ $# -eq 0 ]]; then
        export DHA="$COMPASS_DIR/deploy/conf/virtual_cluster.yml"
    elif [[ "$1" == "five" ]];then
        export DHA="$COMPASS_DIR/deploy/conf/virtual_five.yml"
    else
        file=${1%*.yml}.yml
        if [[ -f $file ]]; then
            export DHA=$file
        elif [[ -f $CONF_DIR/$file ]]; then
            export DHA=$CONF_DIR/$file
        elif [[ -f $COMPASS_DIR/deploy/conf/$file ]]; then
            export DHA=$COMPASS_DIR/deploy/conf/$file
        else
            exit 1
        fi
    fi
}

function generate_input_env_file()
{
    ofile="$WORK_DIR/script/deploy_input.sh"

    echo  '#input deployment  parameter' > $ofile

    cfg_file=`ls $COMPASS_DIR/deploy/conf/{base,"$TYPE"_"$FLAVOR",$TYPE,$FLAVOR,compass}.conf 2>/dev/null`
    option_name=`get_option_name_list "$cfg_file"`
    option_flag=`get_option_flag_list "$option_name"`

    TEMP=`getopt -o h -l dha:,network:,neutron:,conf-dir:,$option_flag -n 'deploy_parameter.sh' -- "$@"`

    if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi
    eval set -- "$TEMP"
    while :; do
        if [[ "$1" == "--" ]]; then
            shift
            break
        fi

        option=`echo ${1##-?} | tr [:lower:] [:upper:] | sed 's/-/_/g'`
        echo "export $option=$2" >> $ofile
        shift 2
        continue

    done

    echo $ofile
}

function process_default_para()
{
    if [[ -z $CONF_DIR ]]; then
         local set conf_dir=${COMPASS_DIR}/deploy/conf
    else
         local set conf_dir=$CONF_DIR
    fi

    get_conf_name $*
    python ${COMPASS_DIR}/deploy/config_parse.py \
           "$DHA" "$conf_dir" \
           "${COMPASS_DIR}/deploy/template" \
           "${WORK_DIR}/script" \
           "deploy_config.sh"

    echo ${WORK_DIR}/script/deploy_config.sh
}

function process_input_para()
{
    input_file=`generate_input_env_file $config_file $*`

    echo $input_file
}
