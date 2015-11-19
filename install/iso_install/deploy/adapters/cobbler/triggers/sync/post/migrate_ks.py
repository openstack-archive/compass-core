#!/usr/bin/python
"""script to migrate rendered kickstart files from cobbler to outside."""
import logging

from cobbler import api


def main():
    """main entry"""
    cobbler_api = api.BootAPI()
    for system in cobbler_api.systems():
        cobbler_api.kickgen.generate_kickstart_for_system(system.name)
        try:
            with open(
                '/var/www/cblr_ks/%s' % system.name, 'w'
            ) as kickstart_file:
                logging.info("Migrating kickstart for %s", system.name)
                data = cobbler_api.kickgen.generate_kickstart_for_system(
                    system.name)
                kickstart_file.write(data)
        except Exception as error:
            logging.error("Directory /var/www/cblr_ks/ does not exist.")
            logging.exception(error)
            raise error


if __name__ == '__main__':
    logging.info("Running kickstart migration")
    main()
