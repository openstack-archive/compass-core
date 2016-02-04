#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
reset=`tput sgr0`
red=`tput setaf 1`
green=`tput setaf 2`
yellow=`tput setaf 3`

function log_info() {
    echo -e "${green}$*${reset}"
}

function log_warn() {
    echo -e "${yellow}$*${reset}"
}

function log_error() {
    echo -e "${red}$*${reset}"
}

function log_progress() {
    echo -en "${yellow}$*\r${reset}"
}

