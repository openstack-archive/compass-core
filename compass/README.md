Compass Core Python Modules
===========================
`compass/` is where all the core python modules of compass are, including API, DB, tasks and installers and so on.

##Direcotries and Files

        * actions/ - compass heavy-lifting actions. This directory includes wrappers of heavy-lifting utility functions,
            such as clean.py, delete.py and deploy.py. It also has complete modules, e.g. health_check/ that does a health   
            check on compass and output diagnoses. 
        * api/ - API related files go here.
            * api.py - defines compass RESTful API. 
            * api.raml - raml file to display/document compass RESTful api.
            * auth_handler.py - handles API authentication.
            * exception_handlers.py - handles API exceptions.
            * utils.py - utilities for API.
            * v1/ - deprecated directory.
        * apiclient/ - API client.
            * example.py - example code to deploy a cluster by calling compass API client.
            * restful.py - compass API client library.
            * v1/ - deprecated directory.a
        * db/ - compass database modules.
            * api/ - Database level API interfaces, which includes all compass primitive data types.
            * callback.py - metadata callback methods.
            * config_validation/ - configuration validation module.
            * exception.py - compass defined exceptions for database module.
            * models.py - database model file, defining all compass database tables.
            * validator.py - database validation methods.
            * vi/ - deprecated directory.
        * deployment/ - backend deployment module that handles upstream data and dumps to installers
            * deployment_manager.py - deployment dispatcher that defines interfaces and retrieves/updates configurations.
            * installers - contains base installers and its children installers such as os_installer and pk_installer
              (package_installer). These installers here are the "plugin" kind of files that interact with installer
              tools(e.g. chef) that do the real installation tricks.
            * utils/ - utility module that contains a constant.py which defines all keyword variables for deployment.
        * hdsdiscovery/ - hardware discovery module, mainly for mac-address retrieval from switches.
            * base.py - a base class that can be extended by vendors under vendor/ directory.
            * error.py - hdsdiscovery module error handling.
            * hdmanager.py - manages hdsdiscovery functionalities.
            * SNMP_CONFIG.md - instructions on how to install and configure snmp related modules/packages.
            * utils.py - contains utility functions for hdsdiscovery.
            * vendors/ - switch/hardware vendor specific plugins. To support a new vendor:
                    1. Make sure the switch product supports SNMP.
                    2. Make sure the switch product uses standard MIB.
                    3. Add a corresponding plugin under vendors/.
                using arista as an example, first a python file with the same name of its parent directory should be added
                (e.g: arista.py). Define the class_name in the vendor file as "Arista" and give the class identical name.
                Then create a subdirectory called "plugins" and place mac.py under it.
        * log_analyzor/ - compass progress tracking module.
            * adapter_matcher.py - module to provide installing progress calculation for the adapters.
            * file_matcher.py - updates installing progresses by processing the log files.
            * line_matcher.py - updates/gets progress when a matched line is found in log files.
            * progress_calculator.py: provides functions to update installing progresses.
        * tasks/ - all celery tasks are defined here.
            * client.py - module to setup celery client.
            * tasks.py - defines all celery tasks.
        * tests/ - all unittest code
        * test_serverside/ - tests for installers(now only supports chef).
        * utils/ - compass core module utility functions.
