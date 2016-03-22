Install Scripts for Compass
===========================

You can install Compass to a CentOS-6.5/6.6 system by running install scripts.

##Quick steps to install Compass

i. run ```./install.sh```

ii. install.sh will pop up questions to understand your configurations. It will provide default values based on calculated results. For a more detailed explanation of these questions please [visit Compass user doc on Compass official site](http://www.syscompass.org/install.html#step-one). In most cases, using the default values will do the trick
(Please note that docs on `syscompass.org` may not be up-to-date and installation NIC of compass should have a private subnet IP instead of management IP which is suggested by the docs).

iii. After answering all the questions, install.sh will take over the installation. The whole process may take 30-45 minutes depending on your network latency and the choices you made.

##Files

    * ansible.sh - script to install ansible package, called by install.sh.
    * chef.sh - script to install and configure chef-server and knife, called by install.sh.
    * cobbler.sh - script to install and configure cobbler server, called by install.sh
    * compass.sh - script to install and configure compass and its components, called by install.sh
    * compass_web.sh - script to setup compass front-end UI and http server for local repositories, called by install.sh
    * dependency.sh - script to install all the dependency packages for compass, called by install.sh
    * install.conf - conf file that contains all the variables used by all sh files. You can give default values to
      variables so that install script will not ask questions. Examples will be given in next section.
    * install.conf.template - a template/example for install.conf, this file is used by compass regtest to install compass.
    * install_func.sh - contains the common functions for all scripts.
    * install.sh - main entrance.
    * prepare.sh - script to prepare environments, pre-download ISOs and update services/packages.
    * setup_env.sh - script to cache all the user inputs and persist the inputs into an env.conf file for scripts to use.
      This makes sure that when somehow the install process is aborted, running each script file separtely still works.

##Example of install.conf variables(for developers)
For example, in install.conf there's no default value set for NIC variable, thus install.sh will ask you to fill in during the script run:


    export NIC=${NIC:-}
If you give it a default value, install.sh will take it and skip the question:

    export NIC=$(NIC:-eth0}
Now *eth0* will be used by install.sh to answer the question of `Please enter the NIC:` If you wish to contribute to compass and add your own variables for compass install scripts to use, you can simply call `loadvars()` function in `install.sh`:

    loadvars foo "bar"
Adding this line to `install.sh` will result in a new question being asked as:
"```Please enter the foo```" and the default value for `foo` is `bar`.

You would also need to add

    foo=\${foo:-$foo}
into `setup_env.sh` to make sure the user input value gets persisted into `env.conf`.

##Q&A
Q: I am a new user of Compass and I do not know too much about DevOps. I am not sure how to answer those questions asked by `install.sh`. What should I do?

A: `install.sh` can give default answers based on the calculated results. If you are not sure about your environment, you can just simply follow the default values(press ENTER).

Q: Some questions ask me to provide `Y/N` and won't accept `ENTER` as an answer?

A: Yes those questions are flags for supporting different distributions. If you are not familiar with those distributions, simply answer `Y` to the ones you would like to support. Also answer `Y` to all those questions is not a bad idea.

Q: Installation was aborted for some reason and I do not wish to answer those questions all over again, can I run scripts one by one?

A: Yes, please run the scripts in this order:

`dependency.sh -> prepare.sh -> cobbler.sh -> chef.sh -> ansible.sh -> compass-web.sh -> compass.sh`
