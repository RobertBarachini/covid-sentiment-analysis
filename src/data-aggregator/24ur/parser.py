from bs4 import BeautifulSoup as bs
import os
from pathlib import Path
import json
import sys
from datetime import datetime
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf
import numpy as np
import stats as st

# TODO:
# * add logging and error handling to catch edge cases

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)
processed_json_dir = os.path.join(*[script_dir, "processed/json"])

date_min = datetime(2019, 11, 30)
date_max = datetime(2021, 12, 1)

args = sys.argv[1:]
script_name = "24ur-processor"
print(f"Starting args: {args}")
if len(args) > 0:
	script_name = args[0]
json_name = f"{script_name}.json"

# json_name = "article_links.json"
# json_name = "article_single_tester.json"
# print("EXITING - SAFETY")
# sys.exit(0)

def prettify_html(html):
	# return bs(html).prettify()
	return bs(html, 'html.parser').prettify()

def process_html(article_obj):
	try:
		# Variables from object
		parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
		datetime_filesystem = parsed_timestamp.strftime("%Y-%m-%d_%H-%M")
		article_title = article_obj["title"]
		article_title_safe = uf.get_safe_filename(article_title)
		filename_final = f"{datetime_filesystem} {article_title_safe}.html"
		raw_path = os.path.join(*[script_dir, "raw", filename_final])
		json_path = os.path.join(*[processed_json_dir, f"{filename_final}.json"])
		# print(f"Raw path: {raw_path}")
		# print(f"JSON path: {json_path}")
		# print()
		if not os.path.exists(raw_path) or os.path.exists(json_path):
			# print(f"Input file does not exist or has already been processed.")
			return

		article_json = {}
		# Save the object from which the article was scraped
		article_json["archive_source"] = article_obj
		# Process html
		html = uf.read_from_file(raw_path) 
		html = bs(html, 'html.parser')
		# NOTE - Article header
		article_header = html.find(class_='article__header', recursive=True)
		if not article_header: # probably an ad or article which has been deleted since indexing and before parsing
			article_json["type"] = "deleted"
			return # SKIP article if deleted
		try:
			article_labels_obj = article_header.find_all(class_='article__label')
			article_labels = [article_label.text.strip() for article_label in article_labels_obj]
			if "OGLAS" in article_labels:
				article_json["type"] = "advertisement"
			else:
				article_json["type"] = "article"
			article_json["article_labels"] = article_labels
			article_json["article_label_lead"] = article_labels[0]
		except Exception as e:
			None
		# Title
		try:
			article_title = article_header.find(class_='article__title')
			article_json["article_title"] = article_title.text.strip()
			sentiment_obj = st.get_text_sentiment(article_json["article_title"])
			article_json["article_title_sentiment"] = sentiment_obj
		except Exception as e:
			None
		# Article info
		try:
			# TODO parse further
			article_info = article_header.find(class_='article__info')
			article_json["article_info"] = article_info.text.strip()
		except Exception as e:
			None
		# Reading time
		try:
			reading_time = article_header.find(class_='article__readingtime-time')
			article_json["reading_time"] = reading_time.text.strip()
		except Exception as e:
			None
		# NOTE - Article details
		article_details = html.find_all(class_='article__details')[0]
		# Authors
		try:
			authors = article_details.find_all(class_='article__details-main')[0].find_all("a")
			# TODO add author links
			article_json["authors"] = [author.text.strip().replace(" /", "") for author in authors]
		except Exception as e:
			None
		# Comments - at least how they keep the score - usually this number is less than the number of all actual comments for some reason
		try:
			article_comments_count = article_details.find_all(class_='article__details-main')[1]
			article_json["article_comments_count"] = int(article_comments_count.text.strip())
		except Exception as e:
			None
		# NOTE - Article body
		article_body = html.find_all(class_='article__body')[0] #.text.strip()	
		# Summary
		try:
			article_json["article_summary"] = article_body.find_all(class_='article__summary')[0].text.strip()
			sentiment_obj = st.get_text_sentiment(article_json["article_summary"])
			article_json["article_summary_sentiment"] = sentiment_obj
		except Exception as e:
			None
		# Contents
		try:
			article_contents = article_body.find_all(class_='article__body-dynamic dev-article-contents')[0]
			all_p = article_contents.find_all('p')
			article_json["article_contents"] = "\n\n".join([p.text.strip() for p in all_p if len(p.text.strip()) > 0])
			sentiment_obj = st.get_text_sentiment(article_json["article_contents"])
			article_json["article_contents_sentiment"] = sentiment_obj
		except Exception as e:
			None
		# NOTE - Article tags
		article_tags = html.find(class_="article__tags").find_all(class_='article__tag')
		try:
			article_json["article_tags"] = [tag.text.strip() for tag in article_tags]
		except Exception as e:
			None
		# NOTE - Comments
		comments_containers = html.find_all(class_='comments')
		comments_json = []
		for comments_container in comments_containers:
			comments = comments_container.find_all(class_='comment')
			last_toplevel_comment = "-1"
			for comment in comments:
				try:
					if "comment--add" in comment.attrs["class"]:
						continue
					comment_dict = {}
					comment_dict["id"] = comment.attrs["id"]
					comment_dict["timestamp"] = comment.find(class_='comment__timestamp').text.strip()
					comment_dict["body"] = comment.find(class_='comment__body').text.strip()
					sentiment_obj = st.get_text_sentiment(comment_dict["body"])
					comment_dict["sentiment"] = sentiment_obj["sentiment"]
					comment_dict["sentiment_positive_count"] = sentiment_obj["positive_count"]
					comment_dict["sentiment_negative_count"] = abs(sentiment_obj["negative_count"])
					comment_dict["sentiment_word_count"] = sentiment_obj["count"]
					# comment_dict["sentiment_object"] = sentiment_obj
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
				except Exception as e:
					None
		if comments_containers:
			article_json["comments"] = comments_json
			article_json["scraped_comments_count"] = len(comments_json)
		# NOTE - Write to file
		uf.write_to_file(json_path, json.dumps(article_json, indent=2)) #os.path.join(*[processed_json_dir, f"{filename}.json"]), json.dumps(article_json, indent=2))
	except Exception as e:
		# print(f"Exception in process_html: {e}")
		None

def get_matching_files(path, file_extension):
	return [f for f in os.listdir(path) if f.endswith(file_extension)]

def filter_by_time(articles_dict):
	for article_obj_key in list(articles_dict.keys()):
		article_obj = articles_dict[article_obj_key]
		parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
		if not (date_min < parsed_timestamp < date_max):
			del articles_dict[article_obj_key]
	return articles_dict

def process_all_html_files(path):
	articles_index = json.loads(uf.read_from_file(os.path.join(script_dir, json_name)))
	articles_index = filter_by_time(articles_index)
	print(f"Processing {len(articles_index.values())} articles.")
	for i, article_obj in enumerate(articles_index.values()):
		# Condition for individual article testing
		# if article_obj["date"] != "2021-11-20_00-15":
		# 	continue
		try:
			print(f"Processing article {i + 1} of {len(articles_index.values())}.")
			process_html(article_obj)
		except Exception as e:
			print(f"Exception processing {article_obj['link']}: {e}")
		# NOTE - for testing purposes
		# if i == 50:
		# 	break

if __name__ == "__main__":
	# process_html(os.path.join(os.path.join(*[script_dir, "raw"]), "2021-11-19_22-43 Interpelacija Simone Kustec_ 'Ko smo jo najbolj potrebovali, je bila odsotna'.html"))
	process_all_html_files(os.path.join(*[script_dir, "raw"]))
	print("Safely processed all")