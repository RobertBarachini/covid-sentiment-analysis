import json
import os
import sys
import numpy as np
import time
import subprocess
import queue
import threading
from datetime import datetime
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf

# TODO chronologically split workloads between workers
# equal segments splits enable more of a sampling approach over the whole timeline/archive
# chronological slpits enable to split workloads in a way that we get the most recent articles first
# + using equal segments and having the last workers only use the last segments which are out of date range it means
# that the workers exit immediately - only first n workers with valid timespans will do work

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)

context = "parsing" # "scraping"

# Context for scrapers / default context
num_workers = 64 # 64
active_workers = 0 #num_workers
script_name = "24ur-runner-scraper"
json_name = "article_links.json"
worker_prefix = "worker_scraper_"
executable_path = f"{os.path.join(script_dir, 'scraper.py')}" #'LOCAL/async_tester.py')}")
# TODO move this to util functions so all functions access the same time
date_min = datetime(2019, 11, 30)
date_max = datetime(2021, 12, 1)

# Context for parsers
if context == "parsing":
	num_workers = 64
	active_workers = 0 #num_workers
	script_name = "24ur-runner-parser"
	json_name = "article_links.json"
	worker_prefix = "worker_parser_"
	executable_path = f"{os.path.join(script_dir, 'parser.py')}" #'LOCAL/async_tester.py')}")
	date_min = datetime(2019, 11, 30)
	date_max = datetime(2021, 12, 1)

# print("EXITING - SAFETY")
# exit()

# Enable logging for this file
log = uf.set_logging(script_name)
log.info(f"Script name: {script_name}")
log.info(f"JSON name: {json_name}")
log.info(f"Worker prefix: {worker_prefix}")
log.info(f"Number of workers: {num_workers}")
log.info("")

message_queue = queue.Queue()

def get_split_workloads(articles_dict):
	# Split dictionary elements into semi-equally-sized lists
	splits = [x.tolist() for x in np.array_split(np.array(list(articles_dict.values())), num_workers)]
	# Convert list of lists into list of dictionaries
	for i, split in enumerate(splits):
		split_dct = [{ element["link"]: element } for element in split]
		split_dct = dict(map(dict.popitem, split_dct))
		splits[i] = split_dct
	return splits

def get_worker_name(worker_index):
	return f"{worker_prefix}{worker_index:0{len(str(num_workers))}}" #.json"

def write_splits_to_file(splits):
	for i, split in enumerate(splits):
		# Worker name is the prefix + the worker number padded with zeros
		full_worker_name = f"{get_worker_name(i)}.json" #f"{worker_prefix}{i:0{len(str(num_workers))}}.json"
		uf.write_to_file(os.path.join(script_dir, full_worker_name), json.dumps(split, indent=2))

def get_article_filepath(article_obj):
	parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
	datetime_filesystem = parsed_timestamp.strftime("%Y-%m-%d_%H-%M")
	article_title = article_obj["title"]
	article_title_safe = uf.get_safe_filename(article_title)
	filename_final = f"{datetime_filesystem} {article_title_safe}{'.html' if context == 'scraping' else '.json'}"
	write_path = os.path.join(*[script_dir, "raw", filename_final])
	if context == "parsing":
		write_path = os.path.join(*[script_dir, "processed", "json", filename_final])
	return write_path

def prepare_workloads():
	articles_dict = json.loads(uf.read_from_file(os.path.join(script_dir, json_name)))
	counter_filter_date = 0
	counter_filter_file_exists = 0
	print(f"{len(articles_dict)} articles in total (before filtering)")
	log.info(f"{len(articles_dict)} articles in total (before filtering)")
	# Filter out articles that are out of range or already exist
	for article_obj_key in list(articles_dict.keys()):
		article_obj = articles_dict[article_obj_key]
		parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
		# Remove out of date range articles
		if not (date_min < parsed_timestamp < date_max):
			counter_filter_date += 1
			del articles_dict[article_obj_key]
		# Remove articles that already exist on disk
		if os.path.exists(get_article_filepath(article_obj)):
			counter_filter_file_exists += 1
			del articles_dict[article_obj_key]
	print(f"{counter_filter_date} articles filtered out of date range")
	log.info(f"{counter_filter_date} articles filtered out of date range")
	print(f"{counter_filter_file_exists} articles filtered out because they already exist on disk")
	log.info(f"{counter_filter_file_exists} articles filtered out because they already exist on disk")
	print(f"{len(articles_dict)} articles left after filtering")
	log.info(f"{len(articles_dict)} articles left after filtering")
	splits = get_split_workloads(articles_dict)
	for i, split in enumerate(splits):
		print(f"{len(split)} articles in split {i}")
		log.info(f"{len(split)} articles in split {i}")
	write_splits_to_file(splits)
	return splits

def enqueue_stream(work_object, queue, type):
	stream = None
	if type == 1:
		stream = work_object["proc"].stdout
	elif type == 2:
		stream = work_object["proc"].stderr
	for line in iter(stream.readline, b''):
		queue.put(f"{type}: {line.decode('utf-8')}")
	stream.close()

def enqueue_process(worker_object, queue):
	proc = worker_object["proc"]
	exit_code = proc.wait()
	queue.put([f"[{get_worker_name(worker_object['index'])}] Exited with code {exit_code}\n", exit_code, worker_object])

def run_worker(worker_index):
	global message_queue
	# global active_workers
	# Worker name is the prefix + the worker number padded with zeros
	full_worker_name = get_worker_name(worker_index)
	print(f"Starting worker [{full_worker_name}]")
	log.info(f"Starting worker [{full_worker_name}]")
	cmd = []
	cmd.append("python")
	cmd.append(executable_path)
	cmd.append(f"{full_worker_name}")
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)#, bufsize=1, universal_newlines=True, close_fds=True)
	proc.daemon = True
	worker_object = {}
	worker_object["proc"] = proc
	worker_object["index"] = worker_index
	thread_output = threading.Thread(target=enqueue_stream, args=(worker_object, message_queue, 1))
	thread_error = threading.Thread(target=enqueue_stream, args=(worker_object, message_queue, 2))
	thread_exit = threading.Thread(target=enqueue_process, args=(worker_object, message_queue))
	worker_object["thread_output"] = thread_output
	worker_object["thread_error"] = thread_error
	worker_object["thread_exit"] = thread_exit
	thread_output.start()
	thread_error.start()
	thread_exit.start()
	# active_workers += 1
	print(f"Started worker [{full_worker_name}]")
	log.info(f"Started worker [{full_worker_name}]")
	return worker_object

def run_workers():
	global message_queue
	# global active_workers
	active_workers = 0
	worker_objects = {}
	for i in range(0, num_workers):
		worker_object = run_worker(i)
		worker_objects[i] = worker_object
		active_workers += 1
	while num_workers > 0:
		line = message_queue.get()
		if line:
			if isinstance(line, list):
				print(f"  {line[0]}", end='')
				exit_code = line[1]
				worker_object_exit = line[2]
				log.info(f"  {line[0]}")
				log.info(f"Worker [{get_worker_name(worker_object_exit['index'])}] exited with code {exit_code}")
				t_out = worker_object_exit["thread_output"]
				t_err = worker_object_exit["thread_error"]
				t_exit = worker_object_exit["thread_exit"]
				# TODO
				# is there an edge case where we'd need to terminate the process by hand
				# Clearing object
				log.info(f"Deleting threads and process from worker_object")
				del worker_object_exit["thread_output"]
				del worker_object_exit["thread_error"]
				del worker_object_exit["thread_exit"]
				del worker_object_exit["proc"]
				# Clearing object from objects dict
				log.info(f"Deleting worker_object from worker_objects")
				del worker_objects[worker_object_exit["index"]]
				# Joining threads
				log.info(f"Joining worker threads.")
				t_out.join()
				t_err.join()
				t_exit.join()
				log.info(f"Worker [{get_worker_name(worker_object_exit['index'])}] joined.")
				active_workers -= 1
				# Restart worker if exit code is not 0
				# TODO add max restart count
				# if exit_code != 0:
				# 	print(f"Restarting [{get_worker_name(worker_object_exit['index'])}] - Reason: Exit-code={exit_code}")
				# 	log.info(f"Restarting [{get_worker_name(worker_object_exit['index'])}] - Reason: Exit-code={exit_code}")
				# 	worker_object_new = run_worker(worker_object_exit["index"])
				# 	worker_objects[worker_object_exit["index"]] = worker_object_new
				# 	active_workers += 1
				# 	log.info(f"Restarted [{get_worker_name(worker_object_exit['index'])}]")
				print(f"Number of active workers: {active_workers}")
			else: # isinstance(line, str):
				# print(f"  {line}", end='') # uncomment this line to see all stdout/stderr
				None
		if active_workers == 0:
			break
		time.sleep(0.01)

if __name__ == "__main__":
	print("Preparing workloads")
	log.info("Preparing workloads")
	prepare_workloads()
	print("Running workers")
	log.info("Running workers")
	run_workers()
	print("Safely finishing __main__")
	log.info("Safely finishing __main__")