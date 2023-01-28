####
####### This Script contains the Logging functionality
####

import logging

def createLogger():
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.DEBUG)
    # Create a console handler
    console_handler = logging.StreamHandler()
    # Set the console handler level to DEBUG
    console_handler.setLevel(logging.DEBUG)
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the formatter for the console handler
    console_handler.setFormatter(formatter)
    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger
