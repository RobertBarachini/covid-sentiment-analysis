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
sys.path.append(os.path.abspath("src"))
import config
import UtilFunctions

# TODO:
# DONE 1. Loop through all the pages
# DONE 2. Loop through all the articles
# DONE 3. Loop through all the comments
# 4. Solve "moving article" issue - cache current page and see changes or refresh pages view each pass
# 5. Add logging
# 6. Handle exceptions and log them
# 7. Write final data to files (pages, articles, comments)

# global variables
driver = None
timeout_new_page_min = 0.5 # 3
timeout_new_page_max = 1.5 # 5
timeout_element = 1.5
polling_element = 0.5
timeout_new_article = 0.5
timeout_exception = 0.5

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)

def write_to_file(filepath, contents):
	if not os.path.exists(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	with open(filepath, 'w', encoding='utf-8') as f:
		try:
			f.write(contents)
		except Exception as e:
			print('Exception writing to file: ' + str(e))

def init_driver():
	global driver
	options = webdriver.ChromeOptions()
	# options.add_argument('--headless')
	options.add_argument('--incognito')
	driver = webdriver.Chrome(chrome_options=options)
	driver.get("about:blank")
	driver.set_window_position(-1000, 0)
	driver.maximize_window()

def get_safe_filename(filename):
	# TODO find replacement characters similar in look
	filename = filename.replace('<', '_').replace('>', '_').replace(':', '_').replace('"', '_').replace('/', '_').replace('\\', '_').replace('|', '_').replace('?', '_').replace('*', '_')
	# filename = filename.replace(".", "_")
	return filename

def main_loop():
	global driver

	# Init driver - moved the code here for better linting hints since there is no type inference with global scope
	options = webdriver.ChromeOptions()
	# options.add_argument('--headless')
	options.add_argument('--incognito')
	driver = webdriver.Chrome(chrome_options=options)
	driver.get("about:blank")
	driver.set_window_position(-1000, 0)
	driver.maximize_window()

	processed_cards = {}
	# IMPORTANT NOTE:
	# When new articles are added the old ones move pages - non-fixed position - check before re-running or resuming manually
	# or match by date released / article url - BETTER
	# pagetest = 1250
	for page in range(10, 11):
		driver.get(f"https://www.24ur.com/arhiv/novice?stran={page}")
		# Container class: "content content--nested latest"
		cards_container = None
		try:
			cards_container = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
					EC.visibility_of_element_located((By.CSS_SELECTOR, "body > onl-root > div.sidenav-wrapper > div.sidenav-content.takeover-base.onl-allow-takeover-click > div.router-content > onl-archive > div > div > div > main > div"))
			)
		except:
			# TODO implement wait exception
			time.sleep(timeout_exception)
		# WebDriverWait(driver, timeout_element, polling_element).until(lambda x: x.find_element_by_class_name("content content--nested latest").is_displayed())
		article_cards = driver.find_elements_by_class_name("timeline__item")
		windows_history = driver.current_window_handle
		for article_card in article_cards:
			try:
				# get link of article_card href
				article_link = article_card.get_attribute("href")
				date_string = "_".join(article_card.text.split("\n")[0:2]).replace(" ", "")
				datetime_object = datetime.strptime(date_string, '%H:%M_%d.%m.%Y') # 12:10_14.11.2021
				# datetime_object = datetime_object.replace(day = 9, month = 9, hour = 9, minute = 9) # testing
				datetime_filesystem = datetime_object.strftime("%Y-%m-%d_%H-%M")
				print(datetime_filesystem)
				print(article_link)
				article_title = article_card.text.split("\n")[3]
				article_title_safe = get_safe_filename(article_title)
				filename_final = f"{datetime_filesystem} {article_title_safe}.html"
				# scroll to next card
				actions = ActionChains(driver)
				actions.move_to_element(article_card).perform()
				# get article_card title
				article_card.send_keys(Keys.CONTROL, Keys.ENTER)
				# switch to new window
				driver.switch_to.window(driver.window_handles[-1])
				# Wait for comments container to load
				comments_container = None
				try:
					comments_container = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
							EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments"))
					)
				except:
					# TODO implement wait exception
					time.sleep(timeout_exception)
				actions = ActionChains(driver)
				actions.move_to_element(comments_container).perform()
				while True:
					try:
						repeat_counter = 0
						comments_more = None
						try:
							comments_more = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
									EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments > div.comments__more > button"))
							)
						except:
							# we presume no new comments can be loaded
							time.sleep(timeout_exception)
							break
						actions = ActionChains(driver)
						actions.move_to_element(comments_more).perform()
						# comments_more.click()
						comments_container_old = None
						try:
							comments_container_old = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
									EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments"))
							)
						except:
							# TODO implement wait exception
							time.sleep(timeout_exception)
						comments_container_old_str = comments_container_old.text
						# Load more comments
						comments_more.send_keys(Keys.ENTER)
						comments_container_new = None
						try:
							comments_container_new = WebDriverWait(driver, timeout=timeout_element, poll_frequency=polling_element).until(
									EC.visibility_of_element_located((By.CSS_SELECTOR, "#onl-article-comments > div > div.comments"))
							)
						except:
							# TODO implement wait exception
							time.sleep(timeout_exception)
						comments_container_new_str = comments_container_new.text
						# Break if content is unchanged
						# WARNING: This is a very weak check, but it works for now
						# NOTE - it can be problematic if we look at a new article where new replies keep being added as the contents keep changing - "forever" while True
						if comments_container_new_str == comments_container_old_str:
							repeat_counter += 1
						if repeat_counter > 5:
							break
						time.sleep(polling_element)
					except:
						# TODO implement exception
						time.sleep(timeout_exception)
				# Save dynamically loaded source
				write_to_file(os.path.join(*[script_dir, "raw", filename_final]), driver.page_source.encode('utf-8').decode('utf-8'))
			except Exception as e:
				# TODO implement exception
				time.sleep(timeout_exception)
			# driver.get(article_link)
			time.sleep(timeout_new_article)
			# Sometimes invalid session id...
			try:
				driver.close()
			except Exception as e:
				action = ActionChains(driver)
				action.send_keys(Keys.CONTROL, "w")
				action.perform()
			try:
				# Sometimes id changes randomly - probably when new articles added and a shift occurs???
				driver.switch_to.window(windows_history)
			except Exception as e:
				None
			# driver.execute_script("window.history.go(-1)")
			# ALTERNATIVE: driver.execute_script("arguments[0].scrollIntoView();", article_card)
			time.sleep(random.uniform(timeout_new_page_min, timeout_new_page_max))

if __name__ == "__main__":
	main_loop()
	driver.quit()
