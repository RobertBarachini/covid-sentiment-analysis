from bs4 import BeautifulSoup as bs
import os
from pathlib import Path
import json

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)
processed_json_dir = os.path.join(*[script_dir, "processed/json"])

def read_file(file_name):
		with open(file_name, 'r', encoding="utf-8") as f:
				return f.read()

def write_to_file(filepath, contents):
	if not os.path.exists(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	with open(filepath, 'w', encoding='utf-8') as f:
		try:
			f.write(contents)
		except Exception as e:
			print('Exception writing to file: ' + str(e))

def prettify_html(html):
	# return bs(html).prettify()
	return bs(html, 'html.parser').prettify()

def process_html(filename):
	html = read_file(os.path.join(*[script_dir, "raw", filename])) 
	html = bs(html, 'html.parser')
	comments_containers = html.find_all(class_='comments')
	article_json = {}
	comments_json = []
	for comments_container in comments_containers:
		comments = comments_container.find_all(class_='comment')
		last_toplevel_comment = "-1"
		for comment in comments:
			if "comment--add" in comment.attrs["class"]:
				continue
			comment_dict = {}
			comment_dict["id"] = comment.attrs["id"]
			comment_dict["timestamp"] = comment.find(class_='comment__timestamp').text.strip()
			comment_dict["body"] = comment.find(class_='comment__body').text.strip()
			comment_dict["author"] = comment.find(class_='comment__author').text.strip()
			comment_dict["likes"] = comment.find_all(class_='icon-text__value')[1].text.strip()
			comment_dict["dislikes"] = comment.find_all(class_='icon-text__value')[2].text.strip()
			comment_dict["type"] = "comment"
			comment_dict["parent"] = ""
			if "comment--reply" in comment.attrs["class"]:
				comment_dict["type"] = "reply"
				comment_dict["parent"] = last_toplevel_comment
			else:
				last_toplevel_comment = comment_dict["id"]
			comments_json.append(comment_dict)
	article_json["comments"] = comments_json
	filename = Path(filename).stem #os.path.basename(filename).stem
	write_to_file(os.path.join(*[processed_json_dir, f"{filename}.json"]), json.dumps(article_json, indent=2))

def get_matching_files(path, file_extension):
	return [f for f in os.listdir(path) if f.endswith(file_extension)]

def process_all_html_files(path):
	for filename in get_matching_files(path, ".html"):
		fpath = os.path.join(processed_json_dir, f"{Path(filename).stem}.json")
		if not os.path.exists(fpath):
			process_html(os.path.join(path, filename))

if __name__ == "__main__":
	process_all_html_files(os.path.join(*[script_dir, "raw"]))
