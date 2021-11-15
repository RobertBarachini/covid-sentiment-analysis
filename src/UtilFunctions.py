import os
import config
import logging

def set_logging(filename):
	if not os.path.isdir("logs"):
		os.makedirs("logs")
	handler = logging.FileHandler(f'logs/{filename}.log', mode="a+", encoding="utf-8")      
	formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')  
	handler.setFormatter(formatter)
	logger = logging.getLogger(filename)
	level = None
	if config.environment == "debug":
		level = logging.DEBUG
	else: 
		level = logging.INFO
	logger.setLevel(level)
	logger.addHandler(handler)
	logger.info("\n")
	logger.info(f"Set up logging for '{filename}' with level '{level}'")
	return logger