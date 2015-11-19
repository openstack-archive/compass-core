#!/bin/bash
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

