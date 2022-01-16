import os
import sys
import json
from datetime import datetime
sys.path.append(os.path.abspath("src"))
import UtilFunctions as uf
import re

# TODO 
# * check if you convert all texts to lower before doing stuff

current_dir = os.getcwd()
script_pathname = os.path.abspath(__file__)
script_dir = os.path.dirname(script_pathname)
processed_json_dir = os.path.join(*[script_dir, "processed/json"])
processed_stats_dir = os.path.join(*[script_dir, "processed/stats"])
positive_words_filepath = os.path.join(*["models/external/Slovene_sentiment_lexicon_KSS1.1", "positive_words_Slolex.txt"])
negative_words_filepath = os.path.join(*["models/external/Slovene_sentiment_lexicon_KSS1.1", "negative_words_Slolex.txt"])

positive_words = None
negative_words = None

def unique_wordcounts(dirpath):
	words_count = 0
	characters_count = 0
	comments_count = 0
	articles_count = 0
	words = {}
	characters = {}
	json_files = [f for f in os.listdir(dirpath) if f.endswith(".json")]
	for i, json_file in enumerate(json_files):
		print(f"\rProcessing {i+1}/{len(json_files)}", end="")
		articles_count += 1
		json_path = os.path.join(*[dirpath, json_file])
		article_obj = json.loads(uf.read_from_file(json_path))
		if "comments" in article_obj:
			for comment in article_obj["comments"]:
				comments_count += 1
				comment_words = re.sub(r'\W+', ' ', comment["body"].lower()).split()
				for word in comment_words:
					words_count += 1
					if word in words:
						# TODO create objects so you can add frequencies and such
						# words[word]["count"] += 1
						words[word] += 1
					else:
						# words[word] = {"count": 1}
						words[word] = 1
					for char in word:
						char = str(char)
						characters_count += 1
						if char in characters:
							# charachers[char]["count"] += 1
							characters[char] += 1
						else:
							# characters[char] = {"count": 1}
							characters[char] = 1
		# For testing purposes
		# if i == 100:
		# 	break
	print("\n")
	# Add relative frequencies for words and characters
	print(f"Adding relative frequencies for words and characters")
	for word in words:
		words[word] = { "count": words[word], "frequency": words[word] / words_count }
	for char in characters:
		characters[char] = { "count": characters[char], "frequency": characters[char] / characters_count }
	print("Sorting words...")
	words = sorted(words.items(), key=lambda x: x[1]["count"], reverse=True)
	print("Sorting characters...")
	characters = sorted(characters.items(), key=lambda x: x[1]["count"], reverse=True)
	print(f"Total articles: {articles_count}")
	print(f"Total comments: {comments_count}")
	print(f"Total words: {words_count}")
	print(f"Total characters: {characters_count}")
	print(f"Number of unique words: {len(words)}")
	print(f"Number of unique characters: {len(characters)}")
	print(f"Most word occurences: {next(iter(words))}")
	print(f"Most character occurences: {next(iter(characters))}")
	print(f"Average characters per word: {characters_count / words_count}")
	print(f"Average words per comment: {words_count / comments_count}")
	print(f"Average comments per article: {comments_count / articles_count}")
	# Print relative frequencies characters expressed as percentages rounded to 3 decimals
	print("\nRelative frequencies for characters (%)")
	for char in characters:
		print(f"{char[0]}: {round(char[1]['frequency'] * 100, 3)} %    ; ({char[1]['count']} -> {char[1]['frequency']})")
	print("Writing to file...")
	uf.write_to_file(os.path.join(*[processed_stats_dir, "words.json"]), json.dumps(words, indent=2))
	uf.write_to_file(os.path.join(*[processed_stats_dir, "characters.json"]), json.dumps(characters, indent=2))
	print("Done!")
	return words, characters

def init_words_dict(words_filepath, sentiment_value):
	filestr = uf.read_from_file(words_filepath)
	words = filestr.split("\n")
	words_dict = {}
	for word in words:
		words_dict[word] = sentiment_value
	return words_dict

def get_text_sentiment(text):
	global positive_words, negative_words
	if not positive_words:
		positive_words = init_words_dict(positive_words_filepath, 1)
	if not negative_words:
		negative_words = init_words_dict(negative_words_filepath, -1)
	words = re.sub(r'\W+', ' ', text.lower()).split()
	positive_count = 0
	negative_count = 0
	pos_dict = {}
	neg_dict = {}
	for word in words:
		if word in positive_words:
			positive_count += positive_words[word]
			# TODO maybe save a count of how many times a word appears in the text for pos/net_dict
			pos_dict[word] = word
		if word in negative_words:
			negative_count += negative_words[word]
			neg_dict[word] = word
	# sentiment = (positive_count + negative_count) / len(words)
	# Condition to solve devision by zero
	sentiment = 0 if (positive_count + abs(negative_count)) == 0 else (positive_count + negative_count) / (positive_count + abs(negative_count))
	ret_obj = {
		"positive_count": positive_count, 
		"negative_count": abs(negative_count),
		"count": len(words),
		"sentiment": sentiment,
		"positive_list": list(pos_dict.values()),
		"negative_list": list(neg_dict.values())
	}
	return ret_obj	

def test_get_text_sentiment():
	text = "To je izredno abnormalen in slab članek."
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()

	text = "Našim prijateljem se bo zgodilo nekaj dobrega."
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()

	text = "Nova različica novega koronavirusa, ki so jo odkrili v Južni Afriki, se zaradi nenavadno velikega števila mutacij zelo hitro širi in bi lahko zaobšla imunost, pridobljeno s cepljenjem oziroma po prebolelem covidu, opozarjajo znanstveniki. Svetovna zdravstvena organizacija je različico B.1.1.529 označila za skrb vzbujajočo in jo poimenovala omikron. Evropska komisija pa je članicam predlagala, naj omejijo potovanja z juga Afrike in odpovejo letalske povezave s to regijo. Te so nato sklenile dogovor o začasni ustavitvi letov iz sedmih južnoafriških držav."
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()
	
	text = "nekako je to postal boj za osebno dostojanstvo . Ali si blazinica za bucke .. ali pa ne smeš v trgovski center. Usekano, da bolj ne more biti. Trenutno takle mamo in kot vedno, če neko stvar dosti dolgo ponavljaš, to postane družbena norma. Izgleda, da je to cilj s tem posiljevanjem"
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()
	
	text = "Oprostite, vi ste bedak!"
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()
	
	text = "V naslednjih dveh minutah bom povedal svoje subjektivno mnenje o SiOL-u, zatorej me NE prekinjajte in si ne mislite, da vam to govorim kot grožnjo, temveč vzemite to kot OSEBNO! ,SUBJEKTIVNO!, mnenje o SiOL-u. No, pa začnimo. SiOL je najbolj beden, najbolj smrdljiv, najbolj kretenski internetni ponudnik v Sloveniji. Že dejstvo, da vsakič, k mi SiOL ne dela, da moram poklicat na vašo POFUKANO modro številko – k si jo lahko tud zarinete u rt bajdvej – morm čakat eno POFUKANO uro, da dobim enga KRETENA na telefon, k mi pol reče: »Ja, gospod, a ste že probal reseterat modem?« Ma, MRŠ U PIČKO MATER in ta modem, da ti jebem mater u pičko! A ti je jasn? Jebem ti mater nesposobno; pa kere mongoloide pofukane date tja na telefon, prekleti kreteni neumni. Že to kaže o vaši malomarnosti do nas uporabnikov in bi mogl resno razmislt o KVALITETI vašega interneta, NE pa o KVANTITETI, da vam jebem mater u pičko. Nimate nobenih informacij zmer k pokličem, rečete: »Uh, ja, ne vemo tlele, gospod, uh, proti, uh, k ja, uh, tlele k gre proti Nemčiji se neki ustav … « Ma, MRŠ U PIČKO MATER, ti jebem mater u pizdo, poprav to zdele takoj! Po pa rečete: »Ja, bomo dal naprej, gospod, uh, pa vm bom pol povedu, kva se zgodi, ja, bom dau naprej, ane.« Pa kaj boš dau naprej?! Boš dau kurac seb u rt?!, pizda ti materna, gnila! To je blo moje mišlenje, zdej pa pozor! Jst mislm, da bi vsi mogl preklicat SiOL in jt na DRUG ponudnik interneta, ampak tle pa nastane en POFUKAN, mejhn, ZAJEBEN u PIČKU, problem. IN TO JE! Da so USI ponudniki interneta u Sloveniji poslovni partnerji od SiOL-a. KAJ PA TO POMEN?! DA GRE VSE PREK SiOL-A, PIZDA TI MATERNA, GNILA! MAMU TI JEBEM U PIČKO in SiOL, da ti jebem, kretensko! Jest ne mislm plačvt 7 jurju na mesec, da en pofukan Švaba tmle čez scene strela, da mu jebem mater, k vem, da mam več skilla od njega, a ti je jasno?! Da ti jebem. Gnilo. Pičko. Skratka, če ne bo T-2 mal spremenu stvari na slovenskem trgu, pol bomo šli in bomo zažgal ta POFUKAN SiOL! #!&%#!/®€! To je blo vse, hvala."
	print(text)
	print(json.dumps(get_text_sentiment(text), indent=2))
	print()
	
if __name__ == "__main__":
	unique_wordcounts(processed_json_dir)
	# test_get_text_sentiment()
	print("Safely finished __main__")