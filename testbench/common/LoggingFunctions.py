####
####### This Script contains the Logging functionality
####

import logging


def create_logger(logger_name: str):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    # Create a console handler
    console_handler = logging.StreamHandler()
    # Set the console handler level to DEBUG
    console_handler.setLevel(logging.INFO)
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the formatter for the console handler
    console_handler.setFormatter(formatter)
    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger
