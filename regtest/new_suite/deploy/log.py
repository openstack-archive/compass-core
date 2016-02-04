import logging
import os
loggers = {}
def getLogger(name):
    if name in loggers:
        return loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    log_file = "%s.log" % name
    try:
        os.remove(log_file)
    except:
        pass

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    loggers[name] = logger
    return logger

