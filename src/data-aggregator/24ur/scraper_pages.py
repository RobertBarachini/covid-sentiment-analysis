from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import os
import json
import time
import random
from datetime import datetime
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf

log = uf.set_logging("24ur-scraper-pages")

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)
page_root = "https://www.24ur.com"
cache_filepath = os.path.join(script_dir, "article_links.json")
timeout_element = 10.0
polling_element = 0.25
driver = None
max_retries = 5

def init_driver():
	global driver
	options = webdriver.ChromeOptions()
	# options.add_argument('--headless')
	options.add_argument('--incognito')
	driver = webdriver.Chrome(chrome_options=options)
	driver.get("about:blank")
	driver.set_window_position(-1000, 0)
	driver.maximize_window()
	return driver

def get_page(url, counter=max_retries):
	global driver
	if driver is None:
		driver = init_driver()
	log.info(f"Getting page '{url}'")
	driver.get(url)
	cards_container = None
	must_retry = False
	log.info(f"Waiting for page to load")
	try:
		cards_container = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
				EC.visibility_of_element_located((By.CSS_SELECTOR, "body > onl-root > div.sidenav-wrapper > div.sidenav-content.takeover-base.onl-allow-takeover-click > div.router-content > onl-archive > div > div > div > main > div"))
		)
	except Exception as e:
		log.error(f"Exception while waiting for container: {e}")
		must_retry = True
	if cards_container is None:
		log.error(f"Content not properly loaded within {timeout_element} seconds.")
		must_retry = True
	if must_retry:
		if counter > 0:
			log.info(f"Retrying. Counter = {counter}")
			driver = None
			return get_page(url, counter - 1)
	log.info(f"Page loaded")
	time.sleep(1)
	return driver.page_source

# Scrapes the 24ur.com archive pages for article links
def scrape_pages():
		articles = {}
		write_every_n_pages = 5
		# Load from cache to skip duplicates
		if os.path.exists(cache_filepath):
			articles = json.loads(uf.read_from_file(cache_filepath))
		url = f"{page_root}/arhiv/novice?stran="
		# Iterate through pages within preset range
		for page_num in range(1, 10000):
			url_page = f"{url}{page_num}"
			page = get_page(url_page)
			if page is None:
				log.error(f"Error while getting page '{url_page}'")
				continue	
			log.info(f"Scraping page {page_num}")
			print(f"Scraping page {page_num}")
			soup = bs(page, 'html.parser')
			# uf.write_to_file(f"{script_dir}/soup.html", soup.prettify())
			article_elements_left = soup.findAll('div', attrs={'class': 'timeline__left'})
			article_elements_right = soup.findAll('div', attrs={'class': 'timeline__right'})
			if article_elements_left is None or article_elements_right is None:
				log.error(f"Error while getting elements '{url_page}'")
				continue
			# Construct article links and objects from each page
			for article_left, article_right in zip(article_elements_left, article_elements_right):
				link = f"{page_root}{article_left.parent.get('href')}"
				log.info(f"Processing article link '{link}'")
				date_string = article_left.text.split("\n")[1:][0].strip() # 15:52 19. 11. 2021
				datetime_object = datetime.strptime(date_string, '%H:%M %d. %m. %Y') 
				datetime_filesystem = datetime_object.strftime("%Y-%m-%d_%H-%M")
				title = article_right.find('span', attrs={'class': 'card__title-inside'}, recursive=True).text
				if link in articles:
					log.info(f"Skipping duplicate link '{link}'")
					continue
				article = {}
				article["link"] = link
				article["title"] = title
				article["date"] = datetime_filesystem
				log.info(f"Added article to list\n{json.dumps(article, indent=2)}")
				articles[link] = article
			# for article in articles:
			# 		links.append(article.find('a')['href'])
			# For safety reasons, write to file every n pages
			if page_num % write_every_n_pages == 0:
				uf.write_to_file(cache_filepath, json.dumps(articles, indent=2))
			# Sleep for some time to avoid being banned
			time.sleep(random.uniform(0.5, 2.5))
		# Final write to file
		uf.write_to_file(cache_filepath, json.dumps(articles, indent=2))

if __name__ == '__main__':
		# Test the scraper
		scrape_pages()
