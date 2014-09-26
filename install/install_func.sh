#!/bin/bash
#

copy2dir()
{
    repo=$1
    destdir=$2
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
	    cd -
        else
            echo "create $destdir"
            mkdir -p $destdir
            git clone $repo $destdir
            if [ $? -ne 0 ]; then
                echo "failed to git clone $repo $destdir"
                exit 1
            else
                echo "git clone $repo $destdir suceeded"
            fi
            cd $destdir
	    git checkout $git_branch
            git reset --hard remotes/origin/$git_branch
	    cd -
        fi
	cd $destdir
        if [[ ! -z $ZUUL_REF || ! -z $GERRIT_REFSPEC ]]; then
            if [[ ! -z $ZUUL_REF ]]; then
                git_repo=$ZUUL_URL/$3
                git_ref=$ZUUL_REF
                gitbranch=$ZUUL_BRANCH
            elif [[ ! -z $GERRIT_REFSPEC ]]; then
                git_repo=https://$GERRIT_HOST/$3
                git_ref=$GERRIT_REFSPEC
                gitbranch=$GERRIT_BRANCH
            fi
	    if [[ "$git_branch" == "$gitbranch" ]]; then
                git reset --hard remotes/origin/$git_branch
                git fetch $git_repo $git_ref && git checkout FETCH_HEAD
                if [ $? -ne 0 ]; then
                    echo "failed to git fetch $git_repo $git_ref"
		    cd -
		    exit 1
                fi
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
    url=$1
    package=${2:-$(basename $url)}
    action=${3:-""}
    echo "download $package from $url and run $action"
    if [[ -f /tmp/${package} || -L /tmp/${package} ]]; then
        echo "$package already exists"
    else
        if [[ "$url" =~ (http|https|ftp):// ]]; then
            echo "downloading $url to /tmp/${package}"
            curl -L -o /tmp/${package}.tmp $url
            if [[ "$?" != "0" ]]; then
                echo "failed to download $package"
                exit 1
            else
                echo "successfully download $package"
                mv -f /tmp/${package}.tmp /tmp/${package}
            fi
        else
            cp -rf $url /tmp/${package}
        fi
        if [[ ! -f /tmp/${package} && ! -L /tmp/${package} ]]; then
            echo "/tmp/$package is not created"
            exit 1
        fi
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
        echo "copy /tmp/$package to $destdir"
        destdir=$4
        sudo cp /tmp/$package $destdir
    fi
}
