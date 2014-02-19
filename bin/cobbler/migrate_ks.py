#!/usr/bin/python
"""script to migrate rendered kickstart files from cobbler to outside."""
import xmlrpclib
import logging

from compass.utils import setting_wrapper as setting


def main():
    """main entry"""
    remote = xmlrpclib.Server(setting.COBBLER_INSTALLER_URL, allow_none=True)
    token = remote.login(*setting.COBBLER_INSTALLER_TOKEN)
    systems = remote.get_systems(token)
    for system in systems:
        data = remote.generate_kickstart('', system['name'])
        try:
            with open(
                '/var/www/cblr_ks/%s' % system['name'], 'w'
            ) as kickstart_file:
                logging.info("Migrating kickstart for %s", system['name'])
                kickstart_file.write(data)
        except Exception as error:
            logging.error("Directory /var/www/cblr_ks/ does not exist.")
            logging.exception(error)


if __name__ == '__main__':
    logging.info("Running kickstart migration")
    main()
