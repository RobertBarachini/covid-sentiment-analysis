import json
import os
import sys
import numpy as np
import time
import subprocess
import queue
import threading
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf

num_workers = 2
active_workers = 0 #num_workers
script_name = "24ur-runner"
json_name = "article_links_smol.json"
worker_prefix = "worker_"

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)

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

def prepare_workloads():
	articles_dict = json.loads(uf.read_from_file(os.path.join(script_dir, json_name)))
	splits = get_split_workloads(articles_dict)
	write_splits_to_file(splits)
	return splits

def enqueue_stream(work_object, queue, type):
	stream = None
	if type == 1:
		stream = work_object["proc"].stdout
	elif type == 2:
		stream = work_object["proc"].stderr
	for line in iter(stream.readline, b''):
		# queue.put(str(type) + line.decode('utf-8'))
		# queue.put(f"{type}: {line}")
		# queue.put(line.decode('utf-8'))
		queue.put(f"{type}: {line.decode('utf-8')}")
	stream.close()

def enqueue_process(worker_object, queue):
	# global active_workers
	# active_workers -= 1
	proc = worker_object["proc"]
	exit_code = proc.wait()
	queue.put([f"Exited with code {exit_code}\n", exit_code])
	# TODO how to safely join threads?
	# worker_object["thread_output"].join()
	# worker_object["thread_error"].join()
	# worker_object["thread_exit"].join()
	# TODO restart failed workers if exit_code != 0
	# if exit_code != 0:
	# 	print(f"Restarting [{get_worker_name(worker_object['index'])}] - Reason: Exit-code={exit_code}")
	# 	worker_object = run_worker(worker_object["index"])

def run_worker(worker_index):
	global message_queue
	# global active_workers
	# Worker name is the prefix + the worker number padded with zeros
	full_worker_name = get_worker_name(worker_index)
	cmd = []
	cmd.append("python")
	cmd.append(f"{os.path.join(script_dir, 'scraper.py')}") #'async_tester.py')}")
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
	return worker_object

def run_workers():
	global message_queue
	# global active_workers
	active_workers = num_workers
	worker_objects = {}
	for i in range(0, num_workers):
		worker_object = run_worker(i)
		worker_objects[i] = worker_object
	while num_workers > 0:
		line = message_queue.get()
		if line:
			if isinstance(line, list):
				print(f"  {line[0]}", end='')
				active_workers -= 1
			else: # isinstance(line, str):
				print(f"  {line}", end='')
		if active_workers == 0:
			break
		time.sleep(0.01)
	# for worker_object in worker_objects.values():
	# 	worker_object["thread_output"].join()
	# 	worker_object["thread_error"].join()
	# 	worker_object["thread_exit"].join()

if __name__ == "__main__":
	prepare_workloads()
	run_workers()