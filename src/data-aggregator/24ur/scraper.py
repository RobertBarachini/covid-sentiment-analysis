# from selenium import webdriver and from selenium.webdriver.common.keys import Keys
from typing import cast
from selenium import webdriver
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import os
import time
import random
from datetime import datetime
import sys
import json
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf

# TODO
# randomly pick m proxies from the list of n proxies from https://checkerproxy.net/
# SKIP: "Stran, ki ste jo zahtevali, ne obstaja!" Examaple: https://www.24ur.com/novice/slovenija/tradicionalni-slovenski-zajtrk-s-preverjenim-slovenskim-medom-iz-medexa.html

# Check if more run arguments are present == script initiated as a worker
args = sys.argv[1:]
script_name = "24ur-scraper"
print(f"Starting args: {args}")
if len(args) > 0:
	script_name = args[0]
json_name = f"{script_name}.json"

# Enable logging for this file
log = uf.set_logging(script_name)
log.info(f"Starting args: {args}")

# global variables - rest of them anyways
driver = None
timeout_new_page_min = 0.5 # 3
timeout_new_page_max = 1.5 # 5
timeout_element = 5
timeout_skip_element = 2
polling_element = 0.125
timeout_new_article = 0.5
timeout_exception = 0.5
max_retries = 5
date_min = datetime(2019, 11, 30)
date_max = datetime(2021, 12, 1)
time_per_article = 5 * 60 # 5 minutes

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)

def init_driver():
	global driver
	options = webdriver.ChromeOptions()
	options.add_argument('--incognito')
	options.add_argument('--headless') # uncomment this for bigger workloads - especially when employed as a worker script
	# options.add_argument('--log-level=3')
	# options.add_argument('--disable-logging')
	# options.add_argument('--silent')
	# options.add_argument('--disable-gpu')
	options.add_experimental_option('excludeSwitches', ['enable-logging']) # this ACTUALLY disables logging
	# service_log_path = os.devnull
	# service_log_path = "NUL"
	driver = webdriver.Chrome(chrome_options=options)#, service_log_path=service_log_path)
	driver.get("about:blank")
	driver.set_window_position(-1000, 0)
	driver.maximize_window()
	return driver

# Gets the page and waits for element with selector to load. If skip_condition element is found perform the search first
# and then check for its present. If presence exists and skip_selector element is present wait for an alternative element to load
# before returning the loaded page.
# Example: 
# Skip condition matches an article that represents an advertisement. If driver finds it then it waits for an alternative element
# and returns the result without witing for original skip_condition (example: comments section) as that element is never present.
def get_page(url, selector, skip_condition=None, skip_selector=None, counter=max_retries):
	global driver
	if driver is None:
		driver = init_driver()
	log.info(f"Getting page '{url}'")
	driver.get(url)
	main_container = None
	must_retry = False
	log.info(f"Waiting for page to load")
	skip_element = None
	if skip_condition is not None:
		try:
			skip_element = WebDriverWait(driver, timeout=timeout_skip_element, poll_frequency=polling_element).until(
					EC.visibility_of_element_located(skip_condition)
			)
		except Exception as e:
			None
	if skip_element is None:
		try:
			main_container = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
					EC.visibility_of_element_located(selector)
			)
		except Exception as e:
			log.error(f"Exception while waiting for container: {e}")
			must_retry = True
		if main_container is None:
			log.error(f"Content not properly loaded within {timeout_element} seconds.")
			must_retry = True
		if must_retry:
			if counter > 0:
				log.info(f"Retrying. Counter = {counter}")
				# driver.quit()
				# driver = None
				return get_page(url, selector, skip_condition=skip_condition, skip_selector=skip_selector, counter=counter - 1)
	else:
		log.info(f"Skip condition met.")
		# print(f"Skip condition met.")
		if skip_selector is not None:
			log.info(f"Waiting for skip_selector to load")
			try:
				skip_element = WebDriverWait(driver, timeout=timeout_skip_element, poll_frequency=polling_element).until(
						EC.visibility_of_element_located(skip_selector)
				)
			except Exception as e:
				None
	log.info(f"Page loaded")
	# Some extra wait time just in case
	time.sleep(0.25)
	return driver.page_source

def scrape_article(article_obj):
	start_time = time.perf_counter()
	global driver
	# Reload driver for each article to prevent getting errors on page content reload
	driver = init_driver()
	article_url = article_obj["link"]
	# Main element to wait for
	selector = (By.CSS_SELECTOR, "#onl-article-comments > div > div.comments")
	# Ad box
	skip_condition = (By.CSS_SELECTOR, "body > onl-root > div.sidenav-wrapper > div.sidenav-content.takeover-base.onl-allow-takeover-click > div.router-content > onl-article > div:nth-child(3) > div > div > main > div.article__header > span")
	# Wait for article body instead
	skip_selector = (By.CSS_SELECTOR, "body > onl-root > div.sidenav-wrapper > div.sidenav-content.takeover-base.onl-allow-takeover-click > div.router-content > onl-article > div:nth-child(3) > div > div > main > div.article__body")
	page = get_page(article_url, selector, skip_condition=skip_condition, skip_selector=skip_selector)
	# Important variables
	parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
	datetime_filesystem = parsed_timestamp.strftime("%Y-%m-%d_%H-%M")
	article_title = article_obj["title"]
	article_title_safe = uf.get_safe_filename(article_title)
	filename_final = f"{datetime_filesystem} {article_title_safe}.html"
	temp_path = os.path.join(*[script_dir, "temp", filename_final])
	write_path = os.path.join(*[script_dir, "raw", filename_final])

	skip_element = None
	try:
		skip_element = WebDriverWait(driver, timeout=polling_element, poll_frequency=polling_element).until(
				EC.visibility_of_element_located(skip_condition)
		)
	except Exception as e:
		None
	# Only load more comments if they are actually present - not present when article is an ad
	if skip_element is None:
		# Main loop for dynamically loading the comments
		while True:
			# try:
				repeat_counter = 0
				comments_more = None
				log.info("Waiting for More comments button.")
				try:
					comments_more = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
							EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments > div.comments__more > button"))
					)
				except Exception as e:
					# This is natural when no more comments can be loaded
					log.info("No more comments to load.")
					break
				actions = ActionChains(driver)
				actions.move_to_element(comments_more).perform()
				# comments_more.click()
				comments_container_old = None
				try:
					comments_container_old = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
							EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments"))
					)
				except Exception as e:
					time.sleep(timeout_exception)
					log.error(f"Exception waiting for (old) comments container element:\n{e}")
				comments_container_old_str = comments_container_old.text
				# Load more comments
				log.info("Pressing 'More comments' button.")
				comments_more.send_keys(Keys.ENTER)
				comments_container_new = None
				comments_container_new_str = None
				# Wait for comments to load
				for i in range(0, 5):
					try:
						comments_container_new = WebDriverWait(driver, timeout=1, poll_frequency=polling_element).until(
								EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments"))
						)
					except Exception as e:
						None
						# time.sleep(timeout_exception)
						# log.error(f"Exception waiting for (new) comments container element:\n{e}")
					comments_container_new_str = comments_container_new.text
					if comments_container_new_str != comments_container_old_str:
						# We assume more comments have been loaded
						log.info("More comments loaded.")
						if len(comments_container_new_str) > len(comments_container_old_str):
							log.info("Saving intermittent results to a temp folder")
							uf.write_to_file(temp_path, page.encode('utf-8').decode('utf-8'))
							log.info(f"Intermittent results saved.")
						# print("More content loaded - breaking repeat loop")
						# time.sleep(timeout_exception)
						break
				# WARNING: This is a very weak check, but it works for now
				# NOTE - it can be problematic if we look at a new article where new replies keep being added as the contents keep changing - "forever" while True
				if comments_container_new_str == comments_container_old_str:
					repeat_counter += 1
					log.info(f"Comments container content unchanged. Increasing repeat counter to {repeat_counter}")
					# print(f"Comments container content unchanged. Increasing repeat counter to {repeat_counter}")
				else:
					# Reset the counter if content has changed
					repeat_counter = 0
				if repeat_counter > 5:
					log.info("Repeat counter reached maximum. Breaking.")
					break
				page_source = driver.page_source
				if len(page_source) > len(page):
					page = page_source
				if time.perf_counter() - start_time > time_per_article:
					log.info("Article timeout reached. Breaking.")
					break
				time.sleep(polling_element)
			# except Exception as e:
			# 	log.error(f"Exception while trying to load all comments:\n{e}")
			# 	time.sleep(timeout_exception)
	log.info(f"Comments loaded, writing source to file. ({write_path})")
	# Save dynamically loaded source
	uf.write_to_file(write_path, page.encode('utf-8').decode('utf-8'))
	log.info("Finished writing to file ({write_path})")
	log.info("Removing temp file.")
	if os.path.exists(temp_path):
		os.remove(temp_path)
	driver.close() # driver.quit() takes a considerably longer time than driver.close()
	driver = None

def main_loop():
	articles_dict = {}
	try:
		articles_dict = json.loads(uf.read_from_file(os.path.join(script_dir, json_name)))
	except Exception as e:
		log.error(f"Exception while reading {json_name}: {e}")
		raise Exception(f"Exception while reading {json_name}: {e}")
	for counter, article_obj in enumerate(articles_dict.values()):#articles_dict.values():
		parsed_timestamp = datetime.strptime(article_obj["date"], "%Y-%m-%d_%H-%M")
		datetime_filesystem = parsed_timestamp.strftime("%Y-%m-%d_%H-%M")
		article_title = article_obj["title"]
		article_title_safe = uf.get_safe_filename(article_title)
		filename_final = f"{datetime_filesystem} {article_title_safe}.html"
		write_path = os.path.join(*[script_dir, "raw", filename_final])
		status = None
		if status in article_obj:
			status = article_obj["status"]
		# Only scrape within the time range
		if date_min < parsed_timestamp < date_max:
			# Only scrape if the article hasn't been scraped before
			if not os.path.exists(write_path) and (status is None or status != "completed"):
				log.info(f"Scraping article {article_obj['link']}")
				scrape_article(article_obj)
				article_obj["status"] = "completed"
				# Save updated dictionary objects every n iterations - big objects cause a sizeable delay
				if counter + 1 % 5 == 0:
					log.info(f"Saving updated dictionary objects to {json_name}")
					uf.write_to_file(os.path.join(script_dir, json_name), json.dumps(articles_dict, indent=2))
				# Add some sensible timer before trying to scrape the next article?
				# time.sleep(1)
			else:
				log.info(f"Article {article_obj['link']} already scraped or not eligible")
		else:
			log.info(f"Article {article_obj['link']} out of date range")
	# Save updated dictionary objects
	log.info(f"Saving updated dictionary objects to {json_name} (FINAL)")
	uf.write_to_file(os.path.join(script_dir, json_name), json.dumps(articles_dict, indent=2))

if __name__ == "__main__":
	log.info("Starting main loop")
	main_loop()
	log.info("Finished main loop")
	try:
		driver.quit()
	except Exception as e:
		log.error(f"Exception while quitting driver:\n{e}")
	log.info("Safely exiting")
