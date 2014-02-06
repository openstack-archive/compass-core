#!/usr/bin/python

import xmlrpclib
import logging

from compass.utils import setting_wrapper as setting


def main():
    remote = xmlrpclib.Server(setting.COBBLER_INSTALLER_URL, allow_none=True)
    token = remote.login(*setting.COBBLER_INSTALLER_TOKEN)
    systems = remote.get_systems(token)
    for system in systems:
        data = remote.generate_kickstart('', system['name'])
        try:
            with open('/var/www/cblr_ks/%s' % system['name'], 'w') as f:
                logging.info("Migrating kickstart for %s", system['name'])
                f.write(data)
        except:
            logging.error("Directory /var/www/cblr_ks/ does not exist.")

if __name__ == '__main__':
    logging.info("Running kickstart migration")
    main()
