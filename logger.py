import logging
import os

LOG_DIR = os.path.join("assistant")


class Logger:
    _loggers = {}

    @classmethod
    def get_instance(cls, logger_name):
        if logger_name not in cls._loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)

            log_directory = LOG_DIR
            if not os.path.exists(log_directory):
                os.makedirs(log_directory)

            log_file_path = os.path.join(log_directory, f"{logger_name}.log")

            file_handler = logging.FileHandler(log_file_path)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            cls._loggers[logger_name] = logger
        return cls._loggers[logger_name]


logger = Logger.get_instance("main")
