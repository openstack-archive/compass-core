#!/bin/bash
#

fastesturl()
{
    shortest=99999
    fastest_url=""
    good_code=[200,206]
    while [ $1 ]; do
        url=$1
        result=($(curl --max-time 10 -o /dev/null --header "Range: bytes=0-20000" -s -w "%{http_code} %{time_total}" $url))
        code=${result[0]}
        time=${result[1]}
        if [[ ${good_code[*]} =~ $code ]]; then
            if [ $(echo "$shortest > $time" | bc) -eq 1 ]; then
                shortest=$time
                fastest_url=$url
            fi
        fi
        shift
    done
    if [[ -z $fastest_url ]]; then
        echo "fastesturl not found"
        exit 1
    fi
    echo "$fastest_url"
}

copy2dir()
{
    repo=$1
    destdir=$2
    git_project=$3
    git_branch=master
    if [  -n "$4" ]; then
       git_branch=$4
    fi
    echo "copy $repo branch $git_branch to $destdir"
    if [[ "$repo" =~ (git|http|https|ftp):// ]]; then
        if [[ -d $destdir || -L $destdir ]]; then
            cd $destdir
            git status &> /dev/null
            if [ $? -ne 0 ]; then
                echo "$destdir is not git repo"
		cd -
                rm -rf $destdir
            else
                echo "$destdir is git repo"
		cd -
            fi
        fi

        if [[ -d $destdir || -L $destdir ]]; then
            echo "$destdir exists"
            cd $destdir
            git remote set-url origin $repo
            git remote update
            if [ $? -ne 0 ]; then
                echo "failed to git remote update $repo in $destdir"
		cd -
                exit 1
            else
                echo "git remote update $repo in $destdir succeeded"
            fi
            git reset --hard
            git clean -x -f
            git checkout $git_branch
            git reset --hard remotes/origin/$git_branch
	    git clean -x -f -d -q
	    cd -
        else
            echo "create $destdir"
            mkdir -p $destdir
            git clone $repo $destdir -b $git_branch
            if [ $? -ne 0 ]; then
                echo "failed to git clone $repo $destdir"
                exit 1
            else
                echo "git clone $repo $destdir suceeded"
            fi
        fi
	cd $destdir
        if [[ -z $ZUUL_PROJECT ]]; then
	    echo "ZUUL_PROJECT is not set"
	elif [[ -z $ZUUL_BRANCH ]]; then
	    echo "ZUUL_BRANCH is not set"
        elif [[ -z $ZUUL_REF ]]; then
	    echo "ZUUL_REF is not set"
        elif [[ "$ZUUL_PROJECT" != "$git_project" ]]; then
	    echo "ZUUL_PROJECT $ZUUL_PROJECT is not equal to git_project $git_project"
        elif [[ "$ZUUL_BRANCH" != "$git_branch" ]]; then
	    echo "ZUUL_BRANCH $ZUUL_BRANCH is not equal git_branch $git_branch"
	else
            git_repo=$ZUUL_URL/$ZUUL_PROJECT
            git_ref=$ZUUL_REF
            git reset --hard remotes/origin/$git_branch
            git fetch $git_repo $git_ref
            if [ $? -ne 0 ]; then
                echo "failed to git fetch $git_repo $git_ref"
		cd -
		exit 1
            fi
	    git merge FETCH_HEAD
	    if [ $? -ne 0 ]; then
		echo "failed to git merge $git_ref"
		cd -
		exit 1
	    fi
            git clean -x -f
        fi
	cd -
    else
        sudo rm -rf $destdir
        sudo cp -rf $repo $destdir
        if [ $? -ne 0 ]; then
            echo "failed to copy $repo to $destdir"
            exit 1
        else
            echo "copy $repo to $destdir succeeded"
        fi
    fi
    if [[ ! -d $destdir && ! -L $destdir ]]; then
        echo "$destdir does not exist"
        exit 1
    else
        echo "$destdir is ready"
    fi
}

# TODO(xicheng): Please add comments to ths function. e.g, arg list
download()
{
    #download params: <download url> [<package name>] [<action after package downloaded>]
    force=0
    url=""
    package=""
    options=()
    while [ $# -gt 0 ]; do
	case "$1" in
	    -f | --force)
	        force=1
		shift 1
		;;
	    -u | --url):
	        url=$2
		shift 2
		;;
	    -p | --package):
	        package=$2
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
    if [ -z "$url" ]; then
        url=$1
	shift 1
    fi
    if [ -z "$package" ]; then
        package=${1:-$(basename $url)}
	shift 1
    fi
    echo "download options: $@"
    action=${1:-""}
    downloaded=0
    echo "download $package from $url and run $action"
    if [[ "$force" == "0" || "$force" == "false" ]]; then
        if [[ -f /tmp/${package} || -L /tmp/${package} ]]; then
            echo "$package already exists"
	    downloaded=1
        fi
    fi
    if [[ "$url" =~ (http|https|ftp):// ]]; then
        if [[ "$downloaded" == "0" ]]; then
	    echo "downloading $url to /tmp/${package}"
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
	fi
    else
	echo "copy $url to /tmp/${package}"
        cp -rf $url /tmp/${package}
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
        sudo cp /tmp/$package $destdir
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
