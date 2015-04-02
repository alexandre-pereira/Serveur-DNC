import logging
from logging.handlers import RotatingFileHandler

class Logger:

    logger = None

    @staticmethod
    def initialiser(fileName):
        Logger.logger = logging.getLogger()

        Logger.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s :: %(message)s')
        file_handler = RotatingFileHandler(fileName, 'a', 100000, 1)

        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        Logger.logger.addHandler(file_handler)

        steam_handler = logging.StreamHandler()
        steam_handler.setLevel(logging.INFO)
        Logger.logger.addHandler(steam_handler)

