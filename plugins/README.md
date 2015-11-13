Compass Plugins 
===============

## Overview


Originally, all the configuration files of different target systems for adapter (flavor, os etc) are stored together in conf/adapter (flave, os, etc) directory, there are several problems of this mechanism:
1) it is difficult for compass core install.sh to install configuration files for a specific target systems.
2) it is difficult to distribute configuration files for new target system on an already installed compass system.
The new mechanism is to put each or several related target systems configuration files in a directory, for example, the followng chef_installer
directory under plugins directory will contain all the configuration files for the target systems which will be installed by chef package installer, another use case is, you can put a directory named kilo to include all the configuration files related to kilo. For chef installer
we also move the implementation and tests to plugins directory.

### Directories


    * plugins/ - contains all plugins.

        *  chef_installer/ - contains Chef Installer related configurtion, implementation and unit test files.

                  * adapter/         - contains adapter files related for target systems which will be installed by chef.

                  * flavor/          - contains flavor files related for target system which will be installed by chef.
                  .
                  .
                  .
                  
                  * implementation/  - contains chef package installer python files.
                  
                  * tests/ -           contains unit tests for chef package installer.
