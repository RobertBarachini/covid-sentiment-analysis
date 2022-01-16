import os
import sys
import json
from datetime import datetime
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf
import re
import stats as st

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)
processed_json_dir = os.path.join(*[script_dir, "processed/json"])
processed_csv_dir = os.path.join(*[script_dir, "processed/csv"])

csv_separator = ";"
csv_separator_replacement = ";" # greek question mark that look like semicolon
csv_escape_char = "\\"
# TODO add article headers
article_headers = [

]
comment_headers = [
	"id", "timestamp", "author", "likes", "dislikes", "type", "parent", "body",
	"sentiment", "sentiment_positive_count", "sentiment_negative_count", "sentiment_word_count"
]
comment_headers_extended = comment_headers + [
	"link", "title", "date"
]

def get_safe_value(value):
	# TODO fix this to work properly - replacement works best (for now)
	# return value.replace(csv_separator, f"{csv_escape_char}{csv_separator}{csv_escape_char}") if csv_separator in value else value
	# return value.replace(csv_separator, f"{csv_escape_char}{csv_separator}") if csv_separator in value else value
	# value = re.sub("\W+", " ", value) # TODO improve on this but not on all fields
	try:
		value = value.replace(csv_separator, csv_separator_replacement).replace("\n", " ").replace("\r", " ")
	except Exception as e:
		value = str(value)
	# return value if csv_separator not in value else value.replace(csv_separator, csv_separator_replacement).replace("\n", " ").replace("\r", " ")
	return value

def dict_to_list(obj, headers):
		"""
		Convert a dict to a list using headers used in a csv file
		"""
		return [get_safe_value(obj[h]) if h in obj else "" for h in headers]

def article_to_csv_lists(article_obj):
		"""
		Convert an article to a csv row using headers used in a csv file
		"""
		global comment_headers, comment_headers_extended, article_header
		article_list = None
		# TODO check this
		# article_list = dict_to_list(article_obj, article_headers)
		# NOTE - Comments
		article_comments_list = None
		if "comments" in article_obj:
			article_comments_list = [dict_to_list(h, comment_headers) for h in article_obj["comments"]]
			# Extend the comment object lists with aditional columns from article definition and sentiment analysis
			res_source = dict_to_list(article_obj["archive_source"], ["link", "title", "date"])
			for comment in article_comments_list:
				comment.extend(res_source)
		# NOTE return object creation
		ret_obj = {}
		ret_obj["article_heades"] = article_headers
		ret_obj["article_list"] = article_list
		ret_obj["article_comment_headers"] = comment_headers_extended
		ret_obj["article_comments_list"] = article_comments_list
		return ret_obj

def write_to_csv(path, headers, rows):
	uf.write_to_file(path, "\n".join([f"{csv_separator}".join(headers)] + [f"{csv_separator}".join(r) for r in rows]))

def append_to_csv(path, rows):
	uf.append_to_file(path, "\n".join([f"{csv_separator}".join(r) for r in rows]))

def convert_to_single_csv(dirpath, filename):
	json_files = [f for f in os.listdir(dirpath) if f.endswith(".json")]
	total_wordcount = 0
	comments_count = 0
	hits = 0
	viable = 0
	misses = 0
	a = 0
	header_written = False
	for i, json_file in enumerate(json_files):
		print(f"{i + 1}/{len(json_files)} ; {json_file[:50]}...")
		json_path = os.path.join(*[dirpath, json_file])
		article_obj = json.loads(uf.read_from_file(json_path))
		# if "korona" in article_obj["article_title"].lower():
		# 	a += 1
		# 	if a == 300:
		# 		b = 0
		# if "KORONA" not in article_obj["article_labels"]:
		# 	continue
		# if not ("VIRUS" in article_obj["article_tags"] or "KORONAVIRUS" in article_obj["article_tags"] or "KORONA" in article_obj["article_labels"]):
		# 	misses += 1
		# 	continue
		hitwords = ["virus", "corona", "korona"]
		# Check if any of the word from hitwords is inside the article body or title or labels or summary
		if not any(word in article_obj["article_contents"].lower() for word in hitwords) and \
			not any(word in article_obj["article_title"].lower() for word in hitwords) and \
			not any(word.upper() in article_obj["article_labels"] for word in hitwords) and \
			not any(word.upper() in article_obj["article_tags"] for word in hitwords) and \
			not any(word in article_obj["article_summary"].lower() for word in hitwords):
			misses += 1
			continue
		hits += 1
		res = article_to_csv_lists(article_obj)
		if res["article_comments_list"] == None:
			continue
		viable += 1
		# Test
		for comment in article_obj["comments"]:
			wordcount = len(comment["body"].split())
			total_wordcount += wordcount
			# print(f"    WC comment: {wordcount}")
		comments_count += len(article_obj["comments"])
		# print(f"    WC total: {total_wordcount}")
		#
		#if i == 0:
		if not header_written:
			write_to_csv(os.path.join(*[processed_csv_dir, filename.replace(".json", ".csv")]), res["article_comment_headers"], res["article_comments_list"])
			header_written = True
		else:
			# Append comments from res to csv
			append_to_csv(os.path.join(*[processed_csv_dir, filename.replace(".json", ".csv")]), res["article_comments_list"])
		# For testing smaller batches
		# if i == 100:
		# 	print("Breaking")
		# 	break
	print(f"Hits: {hits}")
	print(f"Misses: {misses}")
	print(f"Viable and processed: {viable}")
	print(f"    Wordcount total: {total_wordcount}")
	print(f"    Comments count: {comments_count}")

def test_article_to_csv_lists():
	article_filename = "2021-11-19_22-43 Interpelacija Simone Kustec_ 'Ko smo jo najbolj potrebovali, je bila odsotna'.html.json"
	article_path = os.path.join(*[processed_json_dir, article_filename])
	article_obj = json.loads(uf.read_from_file(article_path))
	rez = article_to_csv_lists(article_obj)
	# print(f"{csv_separator}".join(rez["article_comment_headers"]))
	# [print(f"{csv_separator}".join(h)) for h in rez["article_comments_list"]]
	write_to_csv(os.path.join(*[processed_csv_dir, article_filename.replace(".json", ".csv")]), rez["article_comment_headers"], rez["article_comments_list"])

def test_dict_to_list():
	test_dict = {
		"a": "1",
		"b": "2;2",
		# "c": "3",
		"d": "4"
	}
	test_headers = ["a", "b", "c", "d"]
	print(",".join(dict_to_list(test_dict, test_headers)))

if __name__ == "__main__":
	# test_dict_to_list()
	# test_article_to_csv_lists()
	convert_to_single_csv(processed_json_dir, "comments.csv")
	print("Safely finished __main__")