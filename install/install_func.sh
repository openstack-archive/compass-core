#!/bin/bash
#
reset=`tput sgr0`
red=`tput setaf 1`
green=`tput setaf 2`
yellow=`tput setaf 3`

function print_info() {
    echo -e "${green}$*${reset}"
}

function print_warn() {
    echo -e "${yellow}$*${reset}"
}

function print_error() {
    echo -e "${red}$*${reset}"
}

function print_progress() {
    echo -en "${yellow}$*\r${reset}"
}

fastesturl()
{
    shortest=99999
    fastest_url=""
    good_code=[200,206]
    while [ $1 ]; do
        url=$1
        result=($(curl -L --max-time 20 -o /dev/null --header "Range: bytes=0-20000" -s -w "%{http_code} %{time_total}" $url))
	if [[ "$?" == "0" ]]; then
	    code=${result[0]}
            time=${result[1]}
            if [[ ${good_code[*]} =~ $code ]]; then
                if [ $(echo "$shortest > $time" | bc) -eq 1 ]; then
                    shortest=$time
                    fastest_url=$url
                fi
            fi
	else
	    echo "ignore failed url $url" >&2
	fi
        shift
    done
    if [[ -z $fastest_url ]]; then
        exit 1
    fi
    echo "$fastest_url"
}

copy2dir()
{
    repo=$1
    destdir=$2

    echo "copy $repo branch $git_branch to $destdir"
    if [[ "$repo" =~ (git|http|https|ftp):// ]]; then
        if [[ -d $destdir/.git ]]; then
            cd $destdir
            git status &> /dev/null
            if [ $? -ne 0 ]; then
                cd -
                rm -rf $destdir
            fi
        fi

        if [[ -d $destdir/.git ]]; then
            cd $destdir
            git remote set-url origin $repo
            git remote update
            if [ $? -ne 0 ]; then
                print_error "failed to git remote update $repo in $destdir"
                cd -
                exit 1
            fi
            git reset --hard
            git clean -x -f
            git checkout $git_branch
            git reset --hard remotes/origin/$git_branch
            git clean -x -f -d -q
            cd -
        else
            mkdir -p $destdir
            git clone $repo $destdir
            if [ $? -ne 0 ]; then
                print_error "failed to git clone $repo $destdir"
                exit 1
            fi
            cd -
        fi
    else
        sudo rm -rf $destdir
        sudo cp -rf $repo $destdir
        if [ $? -ne 0 ]; then
            print_error "failed to copy $repo to $destdir"
            exit 1
        fi
    fi

    if [[ $repo == https://gerrit.opnfv.org/gerrit/compass4nfv ]]; then
        cp $destdir/deploy/adapters/{ansible,cobbler} $destdir/ -rf
    fi
}

# TODO(xicheng): Please add comments to ths function. e.g, arg list
download()
{
    #download params: <download url> [<package name>] [<action after package downloaded>]
    force=0
    urls=()
    package=""
    options=()
    echo "download $@"
    while [ $# -gt 0 ]; do
	case "$1" in
	    -f | --force)
	        force=1
		shift 1
		;;
	    -u | --url):
	        url=$2
		echo "url: $url"
		if [ -z "$url" ]; then
		    echo "url param is empty: $url"
		    exit 1
		fi
	        urls=(${urls[@]} $url)
		shift 2
		;;
	    -p | --package):
	        package=$2
		echo "package: $package"
		if [ -z "$package" ]; then
		    echo "package param is empty: $package"
		    exit 1
		fi
		shift 2
		;;
	    -*)
	        echo "Unknown options: $1"
		shift 1
		;;
	    *)
	        options+=($1)
		shift 1
		;;
	esac
    done
    set ${options[@]}
    if [ ${#urls[@]} -eq 0 ]; then
        urls+=($1)
	shift 1
    fi
    if [ -z "$package" ]; then
	url=${urls[0]}
        package=${1:-$(basename $url)}
	shift 1
    fi
    echo "download options: $@"
    action=${1:-""}
    downloaded=0
    if [[ "$force" == "0" || "$force" == "false" ]]; then
        if [[ -f /tmp/${package} || -L /tmp/${package} ]]; then
            echo "$package already exists"
	    downloaded=1
        fi
    fi
    if [[ "$downloaded" == "0" ]]; then
        if [ ${#urls[@]} -eq 1 ]; then
	    url=${urls[0]}
        else
            echo "download $package from fastest urls ${urls[@]}"
            url=`fastesturl ${urls[@]}`
	    if [[ "$?" != "0" ]]; then
	        echo "failed to get fastest url from ${urls[@]}"
	        exit 1
	    fi
        fi
        if [[ "$url" =~ (http|https|ftp):// ]]; then
	    echo "download $url to /tmp/${package}"
	    if [[ -f /tmp/${package} || -L /tmp/${package} ]]; then
                curl -f -L -z /tmp/${package} -o /tmp/${package}.tmp $url
	    else
		curl -f -L -o /tmp/${package}.tmp $url
	    fi
            if [[ "$?" != "0" ]]; then
                echo "failed to download $package"
                exit 1
            else
                echo "successfully download $package"
		if [[ -f /tmp/${package}.tmp || -L /tmp/${package}.tmp ]]; then
                    mv -f /tmp/${package}.tmp /tmp/${package}
		fi
            fi
        else
	    echo "copy $url to /tmp/${package}"
            cp -rf $url /tmp/${package}
        fi
    fi
    if [[ ! -f /tmp/${package} && ! -L /tmp/${package} ]]; then
        echo "/tmp/$package is not created"
	exit 1
    fi
    if [[ -z "$action" ]]; then
	echo "download $package is done"
	return
    else
	echo "execute $action after downloading $package"
    fi
    if [[ "$action" == "install" ]]; then
        echo "install /tmp/$package"
        sudo rpm -Uvh /tmp/$package
        if [[ "$?" != "0" ]]; then
            echo "failed to install $package"
            exit 1
        else
            echo "$package is installed"
        fi
    elif [[ "$action" == "copy" ]]; then
        destdir=$2
	echo "copy /tmp/$package to $destdir"
        sudo cp -rn /tmp/$package $destdir
	if [[ "$?" != "0" ]]; then
	    echo "failed to copy $package to $destdir"
	    exit 1
	else
	    echo "$package is copied to $destdir"
	fi
    elif [[ "$action" == "unzip" ]]; then
        destdir=$2
	echo "unzip /tmp/$package to $destdir"
	sudo tar -C $destdir -xzvf /tmp/$package
	if [[ "$?" != "0" ]]; then
	    echo "failed to unzip $package to $destdir"
	    exit 1
	else
	    echo "$package is unziped to $destdir"
	fi
    else
	echo "unknown action $action"
	exit 1
    fi
}
