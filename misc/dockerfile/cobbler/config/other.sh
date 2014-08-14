#!/bin/bash
download()
{
    url=$1
    package=${2:-$(basename $url)}
    action=${3:-""}
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
    elif [[ "$action" == "unzip" ]]; then
        unzipped_package=${package%%.zip}
        destdir=$4
        echo "unzip /tmp/$package to /tmp/$unzipped_package and copy to $destdir"
        sudo rm -rf /tmp/$unzipped_package
        pushd `pwd`
        cd /tmp
        sudo unzip -o /tmp/$package
        popd
	sudo cp -rf /tmp/$unzipped_package/. $destdir
    fi
}
