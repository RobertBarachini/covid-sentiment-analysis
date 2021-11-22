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

def write_to_file(filepath, contents):
	if not os.path.exists(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	with open(filepath, 'w', encoding='utf-8') as f:
		try:
			f.write(contents)
		except Exception as e:
			print('Exception writing to file: ' + str(e))

def read_from_file(filepath):
	with open(filepath, 'r', encoding='utf-8') as f:
		return f.read()
		
def get_safe_filename(filename):
	# TODO find replacement characters similar in look
	filename = filename.replace('<', '_').replace('>', '_').replace(':', '_').replace('"', '_').replace('/', '_').replace('\\', '_').replace('|', '_').replace('?', '_').replace('*', '_')
	# filename = filename.replace(".", "_")
	return filename