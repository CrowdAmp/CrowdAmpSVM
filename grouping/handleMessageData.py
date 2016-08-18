import psycopg2
import os
import sys
from testMostLikelyMatches import getMatches
import traceback
from flask import Flask, jsonify, request, json
import requests
import nltk
import re
import csv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cross_validation import train_test_split
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from KaggleWord2VecUtility import KaggleWord2VecUtility
import numpy as np
import random
import urlparse
import pickle
from baseline2 import baseline
from string import punctuation

# Handle grouping, maunally input 5 most common messages

# Undo if mistake

# Send 5 most common messages to influencer
# (i.e. call to influencerDidRespondToPrompt)


# Send responses for top 5 most common messages
# (i.e. call to shouldSendMessageToUsers)

############ 
# Globals
###########
conn = None
cur = None

def executeDBCommand(conn, cur, query):
	cur.execute(query)
	conn.commit()

def promptForInfluencerName():
	influencerName = raw_input("Enter influencerid: ")
	queryStr = "SELECT * FROM influencers WHERE name = '" + influencerName + "';"
	executeDBCommand(conn, cur, queryStr)
	influencer = cur.fetchall()
	if len(influencer) == 0:
		print '\nInvalid influencer name'
		return "-1"
	return influencerName

def promptInfluencer():
	url = 'https://fierce-forest-11519.herokuapp.com/shouldPromptInfluencerForAnswer'
	headers = {'content-type': 'application/json'}
	influencerName = promptForInfluencerName()
	queryStr = "SELECT * from phraseids WHERE influencerid = '" + influencerName + "' AND catchallcategory = 'N' AND prompted = 'N' ORDER BY numusers desc LIMIT 5;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	for row in info:
		phraseid = row[0]
		data = { "phraseId" : str(phraseid) }
		requests.post(url, data=json.dumps(data), headers=headers)
	print 'Influencer has been prompted\n'

def respondToOne(phraseid):
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
	headers = {'content-type': 'application/json'}
	data = { "phraseId" : str(phraseid) }
	requests.post(url, data=json.dumps(data), headers=headers)

def sendResponses():
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
	headers = {'content-type': 'application/json'}
	influencerName = promptForInfluencerName()
	queryStr = "SELECT * from phraseids WHERE influencerid = '" + influencerName + "' AND catchallcategory = 'N' ORDER BY numusers desc;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	for row in info:
		print "sending response to: " + row[1]
		phraseid = row[0]
		data = { "phraseId" : str(phraseid) }
		requests.post(url, data=json.dumps(data), headers=headers)

def sendInfinite():
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
	headers = {'content-type': 'application/json'}
	print 'Warning: This will render this console unusable unless you Ctrl+C to quit\n'
	influencerName = promptForInfluencerName()
	while (1):
		queryStr = "SELECT * from phraseids WHERE influencerid = '" + influencerName + "' AND catchallcategory = 'N' ORDER BY numusers desc;"
		executeDBCommand(conn, cur, queryStr)
		print '\nSending responses infinitely to ' + influencerName + ': Ctrl+C to quit\n'
		info = cur.fetchall()
		for row in info:
			print "sending response to: " + row[1]
			phraseid = row[0]
			data = { "phraseId" : str(phraseid) }
			requests.post(url, data=json.dumps(data), headers=headers)

# TODO: Enhance NLP Stuffs
def displayTopFive(influencerName, phrase, messageid, otherId):
	global conn
	global cur
	validCategories = [str(i) for i in range(0, 101)]
	dbdata = getMatches(conn, cur, influencerName, phrase)
	if len(dbdata) < 5:
		comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
	else:
		comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
	for i in range(0, len(comparisonPhrases)):
		print str(i) + ': ' + comparisonPhrases[i]
	print '\n'
	categoryText = "-1"
	while categoryText not in validCategories:
		#quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
		categoryText = raw_input("Enter category, 100 if none of the above: ")
		if categoryText == 'q':
			return 'q'
		if categoryText == 'u':
			return 'u'
	index = int(categoryText)
	if index == 100 or index >= len(comparisonPhrases):
		phrasegroupid = otherId
	else:
		phrasegroupid = dbdata[index][0]
	queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE userid = (SELECT userid from unprocessedmessages WHERE id = " + str(messageid) + ");"
	executeDBCommand(conn, cur, queryStr)
	previousResponses = cur.fetchall()
	previousPhrasegroups = [previousResponses[i][0] for i in range(0, len(previousResponses))]
	if phrasegroupid in previousPhrasegroups:
		print "FYI That response has already been used"
		#phrasegroupid = otherId Set usealternative to 'True'
		queryStr = "UPDATE unprocessedmessages SET usealternative = 'True' WHERE id = " + str(messageid) + ";"
		executeDBCommand(conn, cur, queryStr)
	queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroupid) + " WHERE id = " + str(messageid) + ";"
	executeDBCommand(conn, cur, queryStr)
	queryStr = "UPDATE phraseids SET numusers = numusers + 1 WHERE id = " + str(phrasegroupid) + ";"
	executeDBCommand(conn, cur, queryStr)
	return 0

# Returns id of the uncategorized group	
def getUncategorized(conn, cur, influencerName):
	queryStr = "SELECT id FROM phraseids WHERE phrasecategories = 'uncategorized';"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	if len(info) == 0:
		print 'No uncategorized, creating one now'
		queryStr = "INSERT INTO phraseids VALUES (DEFAULT, 'uncategorized', '" + influencerName+ "', DEFAULT, 'Y', DEFAULT);"
		executeDBCommand(conn, cur, queryStr)
		queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'uncategorized';"
		executeDBCommand(conn, cur, queryStr)
		info = cur.fetchall()
	uncategorizedId = info[0][0]
	return uncategorizedId

# Reutrns the messageid of the other group
def getOtherId(conn, cur, influencerName):
	queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'other';"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	if len(info) == 0:
		print 'No other category, creating one now'
		queryStr = "INSERT INTO phraseids VALUES (DEFAULT, 'other', '" + influencerName+ "', DEFAULT, 'Y', DEFAULT);"
		executeDBCommand(conn, cur, queryStr)
		queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'other';"
		executeDBCommand(conn, cur, queryStr)
		info = cur.fetchall()
	otherId = info[0][0]
	return otherId

# Used to undo classification mistakes
def recategorizePrevious(conn, cur):
	messageid = raw_input("Type message id of phrase to recategorize or q to continue categorizing new phrases: ")
	if messageid == "q":
		return
	elif not messageid.isdigit():
		print 'Must enter a number for the messageid'
	else:
		mid = int(messageid)
		queryStr = "SELECT * from unprocessedmessages where id = " + messageid + ";"
		executeDBCommand(conn, cur, queryStr)
		info = cur.fetchall()
		if len(info) == 0:
			print 'Not a valid message id'
			return
		previousPhrasegroup = info[0][8]
		influencerName = info[0][2]
		phrase = info[0][1]
		otherId = getOtherId(conn, cur, influencerName)
		print '\n' + phrase
		displayTopFive(influencerName, phrase, mid, otherId)
		queryStr = "UPDATE phraseids SET numusers = numusers - 1 WHERE id = " + str(previousPhrasegroup) + ";"
		executeDBCommand(conn, cur, queryStr)

# TODO: view full conversation

def printFullConversation(conn, cur, messageinfo, manual):
	print 'Displaying tail of conversation \n'
	print 'User ID: ' + str(messageinfo[0][3])
	valid_index_input = []
	queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 5;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	messageid = -1
	if info[0][7] == 'False':
		print "Skipping categorization since last message sent by us"
		return messageid
	for i in range(0, len(info)):
		index = len(info) - 1 - i
		if info[index][7] == 'True':
			messageid = info[index][0]
			print str(index) + ": " + info[index][1]
			valid_index_input.append(str(index))
		else:
			print info[index][1]
	#print messageinfo[0][1]
	phraseindex = -1
	if manual:
		while phraseindex not in valid_index_input:
			phraseindex = raw_input("Enter index of phrase to categorize: ")
		messageid = info[int(phraseindex)][0]
	print 'Message id : '+ str(messageid) +'\n'
	return messageid


def showSuggestion(predictedPhrasegroup, row):
	queryStr = "SELECT phrasecategories FROM phraseids where id = " + str(predictedPhrasegroup) + ";"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	print "Displaying Predicted classification below"
	print "Sentence: " + row[1]
	print "Category: " + info[0][0]
	approval = raw_input("Type 'y' to confirm, u to undo, q to quit, a to add to new category, anything else to reject: ")
	print "\n"
	if approval == 'a':
		phrasegroup = addNewCategory()
		assignToGroup(row[0], phrasegroup, 24, row[3], row[2])
		return 'a'
	if approval == 'y':
		return row[0]
	elif approval == 'q':
		return 'q'
	elif approval == 'u':
		return 'u'
	else:
		return -1

def assignToGroup(messageid, phrasegroup, uncategorizedId, userid, influencerName):	
	otherId = getOtherId(conn, cur, influencerName)
	queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE userid = (SELECT userid from unprocessedmessages WHERE id = " + str(messageid) + ");"
	executeDBCommand(conn, cur, queryStr)
	previousResponses = cur.fetchall()
	previousPhrasegroups = [previousResponses[i][0] for i in range(0, len(previousResponses))]
	if phrasegroup in previousPhrasegroups and phrasegroup != otherId and phrasegroup != uncategorizedId:
		print "FYI that response has already been used"
		#phrasegroupid = otherId
		queryStr = "UPDATE unprocessedmessages SET usealternative = 'True' WHERE id = " + str(messageid) + ";"
		executeDBCommand(conn, cur, queryStr)
	queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE phrasegroup = " + str(uncategorizedId) + " AND userid = '"+ userid +"';"
	executeDBCommand(conn, cur, queryStr)
	queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroup) + " WHERE id = " + str(messageid) + ";"
	executeDBCommand(conn, cur, queryStr)

def manualEdit(conn, cur, influencerName, messageinfo, mid):
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	otherId = getOtherId(conn, cur, influencerName)
	queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
	executeDBCommand(conn, cur, queryStr)
	mid = printFullConversation(conn, cur, messageinfo, True)
	
	#if mid != -1:
	displayTopFive(influencerName, messageinfo[0][1], mid, otherId)

def suggestGroup(conn, cur, influencerName, messageinfo, model, vectorizer):
	mid = printFullConversation(conn, cur, messageinfo, False)
	if mid == -1:
		print "Exiting automation\n"
		return
	
	queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 3;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	
	X_test = []
	for row in info:
		X_test.append(row[1])
	clean_test_set = []

	for i in xrange(0, len(X_test)):
		clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

    # Get a bag of words for the test set, and convert to a numpy array
	test_data_features = vectorizer.transform(clean_test_set)
	test_data_features = test_data_features.toarray()

	predicted = model.predict(test_data_features)
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	phrasegroup = uncategorizedId
	editId = -1
	for i in range(0, len(info)):
		#index = len(info) - 1 - i
		if info[i][7] == 'True':
			editId = showSuggestion(predicted[i], info[i])
			if editId == 'a':
				return 'a'
			if editId == 'q':
				return 'q'
			elif editId == 'u':
				return 'u'
			elif editId != -1:
				phrasegroup = predicted[i]
				assignToGroup(editId, phrasegroup, uncategorizedId, info[i][3], influencerName)
				return -1
		else:
			break
	print "Switching to manual selection"
	manualEdit(conn, cur, influencerName, messageinfo, info[0][0])
	return 0
	#assignToGroup(info[0][0], uncategorizedId, uncategorizedId, info[0][3])

def lastMessageIsSentByUser(messageinfo):
	queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 1;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	if info[0][7] == 'True':
		return True
	else:
		return False

def checkExactMatch(conn, cur, influencerName, messageinfo):
	otherId = getOtherId(conn, cur, influencerName)
	queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 1;"
	executeDBCommand(conn, cur, queryStr)
	lastMessage = cur.fetchall()
	comparisonPhrase = lastMessage[0][1]
	comparisonPhrase = comparisonPhrase.replace("'", "''")
	queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE phrasegroup != 24 AND phrasegroup != -1 AND influencerid = '"+ messageinfo[0][2]+"' AND phrase = '" + comparisonPhrase +"' AND phrasegroup != " + str(otherId) + ";"
	executeDBCommand(conn, cur, queryStr)
	phrasegroups = cur.fetchall()
	if len(phrasegroups) == 0:
		print 'No exact match found in previous records'
		return -1
	phrasenums = [phrasegroups[index][0] for index in range(0, len(phrasegroups))]
	phrasenums.sort()
	phrasegroup = phrasenums[0]
	userid = messageinfo[0][3]
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	queryStr = "SELECT phrasecategories FROM phraseids where id = " + str(phrasegroup) + ";"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	if len(info) > 0:
		response = info[0][0]
		print 'Exact match found in previous records.'
		print 'Assigning: ' + lastMessage[0][1]
		print 'To: ' + response
		print 'Messageid: ' + str(lastMessage[0][0]) + '\n'
		assignToGroup(lastMessage[0][0], phrasegroup, uncategorizedId, userid, influencerName)
	return phrasegroup

def requeueMessage(conn, cur, messageid, uncategorizedId):
	queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(uncategorizedId) + " WHERE id = " + str(messageid) + ";"
	executeDBCommand(conn, cur, queryStr)

def superviseAutomation():
	print "Reviewing automated selections"
	global conn
	global cur
	influencerName = promptForInfluencerName()
	print '\n'
	if influencerName == "-1":
		return
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	otherId = getOtherId(conn, cur, influencerName)
	filename = influencerName + ".p"
	filename2 = influencerName + "train.p"
	model = pickle.load(open( filename, "rb" ) )
	clean_train_set = pickle.load(open( filename2, "rb" ) )
	vectorizer = CountVectorizer(analyzer = "word",   \
                             tokenizer = None,    \
                             preprocessor = None, \
                             stop_words = None,   \
                             max_features = 5000)
	vectorizer.fit_transform(clean_train_set)
	print 'Finished loading model'
	while True:
		queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent LIMIT 1) RETURNING *;"
		executeDBCommand(conn, cur, queryStr)
		messageinfo = cur.fetchall()
		if len(messageinfo) == 0:
			print 'No more uncategorized messages for this influencer \n'
			break
		if lastMessageIsSentByUser(messageinfo):
			if checkExactMatch(conn, cur, influencerName, messageinfo) == -1:
				quit = suggestGroup(conn, cur, influencerName, messageinfo, model, vectorizer)
				if quit == "q":
					requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
					break
				elif quit == "u":
					requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
					recategorizePrevious(conn, cur)
		else:
			assignToGroup(messageinfo[0][0], otherId, uncategorizedId, messageinfo[0][3], influencerName)
			print 'Last message sent by us, skipping'

# -1 indicates failure to classify manually
def groupQuestions():
	global conn
	global cur
	print '\nEnter number that corresponds to question group\n'
	influencerName = promptForInfluencerName()
	print '\n'
	if influencerName == "-1":
		return
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	otherId = getOtherId(conn, cur, influencerName)

	while True:
		queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent desc LIMIT 1) RETURNING *;"
		queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE id > 94531 AND sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent LIMIT 1) RETURNING *;"
		executeDBCommand(conn, cur, queryStr)
		messageinfo = cur.fetchall()
		if len(messageinfo) == 0:
			print 'No more uncategorized messages for this influencer \n'
			break
		queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
		executeDBCommand(conn, cur, queryStr)
		mid = printFullConversation(conn, cur, messageinfo, True)
		if mid != -1:
		#print '\n'
		#print 'Message ID: ' + str(messageinfo[0][0])
		#print 'Context:' + messageinfo[0][5]
		#print messageinfo[0][1] + '\n'	
		# Select and display top 5
			quit = displayTopFive(influencerName, messageinfo[0][1], mid, otherId)
		#quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
			if quit == 'q':
				requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
				break
			elif quit == 'u':
				requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
				recategorizePrevious(conn, cur)
	
def groupNewUsers():
	global conn
	global cur
	print '\nEnter number that corresponds to question group\n'
	influencerName = promptForInfluencerName()
	print '\n'
	if influencerName == "-1":
		return
	uncategorizedId = getUncategorized(conn, cur, influencerName)
	otherId = getOtherId(conn, cur, influencerName)
	#update unprocessedmessages set phrasegroup = -1 where id = (select id from unprocessedmessages where influencerid = 'ChantellePaige' AND phrasegroup = 24 AND userid = (select userid from unprocessedmessages where influencerid = 'ChantellePaige' group by userid having count(*) < 4 limit 1) order by timesent limit 1) returning *;
	while True:
		queryStr = "SELECT DISTINCT * FROM unprocessedmessages WHERE influencerid = '" + influencerName + "' AND userid NOT IN (SELECT DISTINCT userid FROM unprocessedmessages WHERE sentbyuser = 'False' and influencerid = '" + influencerName + "') LIMIT 1;"
		executeDBCommand(conn, cur, queryStr)
		messageinfo = cur.fetchall()
		if len(messageinfo) == 0:
			print 'No more uncategorized messages from NEW USERS for this influencer \n'
			break
		queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
		executeDBCommand(conn, cur, queryStr)
		mid = printFullConversation(conn, cur, messageinfo, True)
		if mid != -1:
			quit = displayTopFive(influencerName, messageinfo[0][1], mid, otherId)
		#quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
			if quit == 'q':
				requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
				break
			elif quit == 'u':
				requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
				recategorizePrevious(conn, cur)

def displayResponses(conn, cur, influencerName):
	queryStr = "SELECT * FROM phraseids WHERE influencerid = '" + influencerName + "' ORDER BY id;"
	executeDBCommand(conn, cur, queryStr)
	categories = cur.fetchall()

	queryStr = "SELECT * FROM responses WHERE influencername = '" + influencerName + "' ORDER BY qid;"
	executeDBCommand(conn, cur, queryStr)
	responses = cur.fetchall()

	for category in categories: 
		print 'Phraseid: ' + str(category[0])
		print 'Group: ' + category[1]
		for response in responses:
			if response[0] == category[0]:
				print 'Response: ' + response[1]
		print '\n'
	return categories, responses

def addAltCategory():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	queryStr = "SELECT * FROM phraseids WHERE influencerid = '" + influencerName + "' ORDER BY id;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	valid = [str(info[i][0]) for i in range(0, len(info))]
	for i in range(0, len(info)):
		print str(info[i][0]) + ": " + info[i][1]
	category = raw_input("Enter phraseid to change: ")
	while category not in valid:
		category = raw_input("Enter phraseid to change: ")
	messageType = raw_input("Enter 'i' for image, anything else for text: ")
	if messageType != 'i':
		text = raw_input("Enter text: ")
		text = text.replace("'", "''")

		queryStr = "INSERT INTO overflowresponses VALUES (" + category + ", '" + text + "', DEFAULT, 'image', '" + influencerName + "', DEFAULT, DEFAULT);"
		executeDBCommand(conn, cur, queryStr)
	else:
		imageName = raw_input("Image Name: ")
		url = raw_input("Image URL: ")
		queryStr = "INSERT INTO overflowresponses VALUES (" + category + ", '" + imageName + "', DEFAULT, 'text', '" + influencerName + "', '" + url + "', DEFAULT);"
		executeDBCommand(conn, cur, queryStr)


	

def deleteResponse(conn, cur, responses, phraseid, influencerName):
	responsePhrases = []
	for response in responses:
		if response[0] == phraseid: 	
			responsePhrases.append(response[1])
	index = 0
	validIndices = []
	for r in responsePhrases:
		validIndices.append(str(index))
		print str(index) + ": " + r
		index += 1
	deleteAll = raw_input("Type 'deleteall' to delete all listed responses or select index of response to delete: ")
	if deleteAll == 'deleteall':
		queryStr = "DELETE FROM responses WHERE qid = " + str(phraseid) + ";"
		executeDBCommand(conn, cur, queryStr)
	elif deleteAll not in validIndices:
		print 'Invalid index'
		return
	else:
		rindex = int(deleteAll)
		refPhrase = responsePhrases[rindex]
		refPhrase = refPhrase.replace("'", "''")
		queryStr = "DELETE FROM responses WHERE influencername = '" + influencerName + "' AND response = '" + refPhrase + "';" 
		executeDBCommand(conn, cur, queryStr)
		
def changeResponse(conn, cur, responses, phraseid, influencerName):
	responsePhrases = []
	for response in responses:
		if response[0] == phraseid: 	
			responsePhrases.append(response[1])
	index = 0
	validIndices = []
	for r in responsePhrases:
		validIndices.append(str(index))
		print str(index) + ": " + r
		index += 1
	phraseindex = raw_input("Select index of response to change: ")
	if phraseindex not in validIndices:
		print 'Invalid index'
		return
	else:
		phraseType = raw_input("Type 'i' to input image, anything else for text: ")
		rindex = int(phraseindex)
		refPhrase = responsePhrases[rindex]
		refPhrase = refPhrase.replace("'", "''")
		if phraseType != 'i':
			newPhrase = raw_input("Type new text: ")
			newPhrase = newPhrase.replace("'", "''")
			queryStr = "UPDATE responses SET response = '" + newPhrase + "' WHERE influencername = '" + influencerName + "' AND response = '" + refPhrase + "';"
			executeDBCommand(conn, cur, queryStr)
		else:
			imageUrl = raw_input("Image url: ")
			imageName = raw_input("Image name: ")
			queryStr = "UPDATE responses SET response = '" + imageName + "' WHERE influencername = '" + influencerName + "' AND response = '" + refPhrase + "';" 
			executeDBCommand(conn, cur, queryStr)
			queryStr = "UPDATE responses SET mediadownloadurl = '" + imageUrl + "' WHERE influencername = '" + influencerName + "' AND response = '" + refPhrase + "';" 
			executeDBCommand(conn, cur, queryStr)
			
	
	
def addResponse(conn, cur, responses, phraseid, influencerName):
	responsePhrases = []
	for response in responses:
		if response[0] == phraseid: 	
			responsePhrases.append(response[1])
	index = 0
	validIndices = []
	for r in responsePhrases:
		validIndices.append(str(index))
		print str(index) + ": " + r
		index += 1

	phraseType = raw_input("Type 'i' to input image, anything else for text: ")
	if phraseType != 'i':
		newPhrase = raw_input("Type new text: ")
		newPhrase = newPhrase.replace("'", "''")
		queryStr = "INSERT INTO responses VALUES (" + str(phraseid) + ", '" + newPhrase +"',DEFAULT, 'text', '" + influencerName + "');"
		executeDBCommand(conn, cur, queryStr)
	else:
		imageUrl = raw_input("Image url: ")
		imageName = raw_input("Image name: ")
		queryStr = "INSERT INTO responses VALUES (" + str(phraseid) + ", '" + imageName + "',DEFAULT, 'image', '" + influencerName + "', DEFAULT, DEFAULT,'" + imageUrl + "');"
		executeDBCommand(conn, cur, queryStr)

def changeCategoryText():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	action = raw_input("Type 'a' to add another response to existing category, 'c' to change response for existing category, 'd' to delete a response: ")
	categories, responses = displayResponses(conn, cur, influencerName)
	validIds = [str(categories[i][0]) for i in range(0, len(categories))]
	print validIds
	phrasegroup = -10
	while phrasegroup not in validIds:
		phrasegroup = raw_input("Enter valid phraseid from those listed above: ")
	phraseid = int(phrasegroup)
	if action == 'd':
		deleteResponse(conn, cur, responses, phraseid, influencerName)
		print "Response deleted \n"
	if action == 'c':
		changeResponse(conn, cur, responses, phraseid, influencerName)
		print "Reponse Changed\n"
	if action == 'a':
		addResponse(conn, cur, responses, phraseid, influencerName)
		print "Response Added\n"

def addNewCategory():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	categoryType = raw_input("Enter 1 for image anything else otherwise: ")
	categoryText = raw_input("Enter new category phrase: ")
	categoryText = categoryText.replace("'", "''")
	queryStr = "INSERT INTO phraseids VALUES (DEFAULT, '" + categoryText + "', '" + influencerName + "', DEFAULT, 'N', DEFAULT, 'N') RETURNING id;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	phrasegroup = info[0][0]	
	if categoryType != '1':
		responseText = raw_input("Response Text (press enter to leave empty): ")
		if responseText == '':
			return phrasegroup
		responseText = responseText.replace("'", "''")
		queryStr = "INSERT INTO responses VALUES (" + str(phrasegroup) + ", '" + responseText +"',DEFAULT, 'text', '" + influencerName + "');"
		executeDBCommand(conn, cur, queryStr)
	else: 
		imageUrl = raw_input("Image url: ")
		imageName = raw_input("Image name: ")
		queryStr = "INSERT INTO responses VALUES (" + str(phrasegroup) + ", '" + imageName + "',DEFAULT, 'image', '" + influencerName + "', DEFAULT, DEFAULT,'" + imageUrl + "');"
		executeDBCommand(conn, cur, queryStr)
	print "Entered new category, phrasegroup:", phrasegroup
	return phrasegroup
	

def displayUnprocessedMessages():
	global conn
	global cur
	print 'Displaying all messages'
	queryStr = "SELECT * FROM unprocessedMessages WHERE sentbyuser = 'True';"	
	executeDBCommand(conn, cur, queryStr)
	dbdata = cur.fetchall()
	for row in dbdata:
		print 'Context: ' + row[5]
		print row[1] + '\n'

def textAll():
	global conn
	global cur
	queryStr = "SELECT DISTINCT userid FROM unprocessedmessages;"
	executeDBCommand(conn, cur, queryStr)
	data = cur.fetchall()
	numberlist = []
	for number in data:
		if number[0][0] == '+':
			numberlist.append(number[0])
	print 'Sending message to: ' + str(numberlist)
	test = ['+19375221858', '+15034966700']
	inputContent = raw_input("Enter phrase to send to all users: ")
	for userid in numberlist:
		data = { "content" : inputContent, "influencerId" : "electionfails", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
		url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
		headers = {'content-type': 'application/json'}
		requests.post(url, data=json.dumps(data), headers=headers)

def sendImageToAll():	
	global conn
	global cur
	queryStr = "SELECT DISTINCT userid FROM unprocessedmessages;"
	executeDBCommand(conn, cur, queryStr)
	data = cur.fetchall()
	numberlist = []
	for number in data:
		if number[0][0] == '+':
			numberlist.append(number[0])
	print 'Sending message to: ' + str(numberlist)
	test = ['+19375221858', '+15034966700']
	inputContent = raw_input("Enter firebase url: ")
	mediaurl = raw_input("Enter media url: ")
	for userid in numberlist:
		data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
		url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
		headers = {'content-type': 'application/json'}
		requests.post(url, data=json.dumps(data), headers=headers)


def textOne():
	global conn
	global cur
	queryStr = "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' AND conversationid != -2 LIMIT 1;"	
	executeDBCommand(conn, cur, queryStr)
	dbdata = cur.fetchall()
	userid = dbdata[0][3]
	print dbdata[0][1]
	print userid
	inputContent = raw_input("Enter phrase to send: ")
	data = { "content" : inputContent, "influencerId" : "morggkatherinee", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
	headers = {'content-type': 'application/json'}
	requests.post(url, data=json.dumps(data), headers=headers)
	queryStr = "UPDATE unprocessedmessages SET conversationid = -2 WHERE id = " + str(dbdata[0][0])	
	executeDBCommand(conn, cur, queryStr)

def sendImageToOne():
	global conn
	global cur
	queryStr = "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' AND conversationid != -2 LIMIT 1;"	
	executeDBCommand(conn, cur, queryStr)
	dbdata = cur.fetchall()
	userid = dbdata[0][3]
	print dbdata[0][1]
	print userid
	inputContent = raw_input("Enter firebase url: ")
	mediaurl = raw_input("Enter media url: ")
	data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
	headers = {'content-type': 'application/json'}
	requests.post(url, data=json.dumps(data), headers=headers)
	queryStr = "UPDATE unprocessedmessages SET conversationid = -2 WHERE id = " + str(dbdata[0][0])	
	executeDBCommand(conn, cur, queryStr)


def textSingleNumber():
	userid = raw_input("Input Number including +1: ")
	inputContent = raw_input("Enter phrase to send: ")
	data = { "content" : inputContent, "influencerId" : "morggkatherinee", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
	headers = {'content-type': 'application/json'}
	requests.post(url, data=json.dumps(data), headers=headers)

def sendImageToSingleNumber():
	userid = raw_input("Input Number including +1: ")
	inputContent = raw_input("Enter firebase url: ")
	mediaurl = raw_input("Enter media url: ")
	data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
	url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
	headers = {'content-type': 'application/json'}
	requests.post(url, data=json.dumps(data), headers=headers)

def showCategories(conn, cur, influencerName):
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]

def printContext(conn, cur, mid, influencerName):
	queryStr = "SELECT * FROM unprocessedmessages WHERE id = " + str(mid) + ";"
	executeDBCommand(conn, cur, queryStr)
	users = cur.fetchall()
	user = users[0][3]
	queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + user + "' AND influencerid = '"+ influencerName+"' ORDER BY timesent desc LIMIT 3;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	print "PRINTING CONTEXT"
	if len(info) >= 3:
		print info[2][1]
	if len(info) >= 2:
		print info[1][1]
	if len(info) >= 1:
		print info[0][1]


def trustModel():
	influencerName = promptForInfluencerName()
	filename = influencerName + ".p"
	filename2 = influencerName + "train.p"
	model = pickle.load(open( filename, "rb" ) )
	clean_train_set = pickle.load(open( filename2, "rb" ) )
	vectorizer = CountVectorizer(analyzer = "word",   \
                             tokenizer = None,    \
                             preprocessor = None, \
                             stop_words = None,   \
                             max_features = 5000)
	vectorizer.fit_transform(clean_train_set)
	print 'Finished loading model'

	global conn
	global cur
	validCategories = [str(i) for i in range(0, 101)]
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	if len(dbdata) < 5:
		comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
	else:
		comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
	for i in range(0, len(comparisonPhrases)):
		print str(i) + ': ' + comparisonPhrases[i]
	print '\n'
	categoryText = "-1"
	while categoryText not in validCategories:
		#quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
		categoryText = raw_input("Enter category: ")
	index = int(categoryText)
	phrasegroupid = dbdata[index][0]
	
	queryStr = "SELECT * FROM unprocessedmessages WHERE sentByUser = 'True' AND phrasegroup = 24 AND influencerid = '" + influencerName + "' ORDER BY timesent;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	
	X_test = []
	for row in info:
		X_test.append(row[1])
	clean_test_set = []

	for i in xrange(0, len(X_test)):
		clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

    # Get a bag of words for the test set, and convert to a numpy array
	test_data_features = vectorizer.transform(clean_test_set)
	test_data_features = test_data_features.toarray()
	predicted = model.predict(test_data_features)
	print predicted
	messageids = []
	messagetext = []
	for i in range(0, len(predicted)):
		if predicted[i] == phrasegroupid:
			messageids.append(info[i][0])
			messagetext.append(info[i][1])
			print info[i][1]
	print '\n'
	for i in range(0, len(messageids)):
		printContext(conn, cur, messageids[i], influencerName)
		print "\n" + str(messageids[i]) + ": " + messagetext[i]
		accept = raw_input("Type 'n' to reject, anything else to accept, q to quit: ")
		if accept == 'q':
			print 'Exiting categorizing, previous categorizations all saved'
			return
		if accept != 'n':
			queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroupid) + " WHERE id = " + str(messageids[i]) + ";"	
			executeDBCommand(conn, cur, queryStr)
		print '\n'
	print str(len(messageids)) + " messages categorized as: " + str(phrasegroupid)

def findInCategory():
	global cur
	global conn
	queryStr = "SELECT * FROM unprocessedmessages WHERE = " + str(phrasegroupid) + " WHERE id = " + str(messageids[i]) + ";"	
	

def retrainModel():
	influencerName = promptForInfluencerName()
	categories = [i for i in range(200)]
	baseline(categories, influencerName)

def promptCategory(influencerName):
	validCategories = [str(i) for i in range(0, 101)]
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
	for i in range(0, len(comparisonPhrases)):
		print str(i) + ': ' + comparisonPhrases[i]
	print '\n'
	categoryText = "-1"
	while categoryText not in validCategories:
		#quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
		categoryText = raw_input("Enter category: ")
	index = int(categoryText)
	phrasegroupid = dbdata[index][0]
	return phrasegroupid
		
def textGroup():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	phrasegroupid = promptCategory(influencerName)
	queryStr = "SELECT userid FROM unprocessedmessages WHERE phrasegroup = " + str(phrasegroupid) + ";"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	userids = []
	for row in info:
		if row[0] not in userids:
			userids.append(row[0])
	print userids
	print len(userids)
	inputContent = raw_input("Enter phrase to send: ")
	approval = raw_input("are you sure? ('y' to confirm): ")
	if approval == 'y':
		for userid in userids:
			data = { "content" : inputContent, "influencerId" : influencerName, "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
			url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
			headers = {'content-type': 'application/json'}
			print data
			requests.post(url, data=json.dumps(data), headers=headers)

def sendPosTwitter(conn, cur, category, influencerName, status):
	queryStr = "SELECT userid FROM unprocessedmessages WHERE phrasegroup = " + category + ";"
	executeDBCommand(conn, cur, queryStr)
	users = cur.fetchall()
	for user in users:
		twitterID = user[0]
		url = 'https://peaceful-mountain-72739.herokuapp.com/updateTwitterAuthorization/' + influencerName + '/' + twitterID + '/' + status
		requests.get(url)
		print 'Posting ' + url


def tweet():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	queryStr = "SELECT * FROM phraseids WHERE influencerid = '" + influencerName + "' ORDER BY id;"
	executeDBCommand(conn, cur, queryStr)
	info = cur.fetchall()
	valid = [str(info[i][0]) for i in range(0, len(info))]
	valid.append("100")
	for i in range(0, len(info)):
		print str(info[i][0]) + ": " + info[i][1]
	category = 'a'
	while category not in valid:
		category = raw_input("Enter phraseid to mark as positive, 100 if none: ")
	if category != "100":
		sendPosTwitter(conn, cur, category, influencerName, 'true')
	category2 = 'b'
	while category2 not in valid:
		category2 = raw_input("Enter phraseid to mark as negative, 100 if none: ")
	if category2 != "100":
		sendPosTwitter(conn, cur, category2, influencerName, 'false')

def updateResponse():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	validids = []
	for row in dbdata:
		print str(row[0]) + ": " + row[1]
		validids.append(str(row[0]))
	responseid = raw_input("Input id to change: ")
	if responseid not in validids:
		print 'Not a valid id'
		return
	responseText = raw_input("Input phrase to add: ")
	responseText.replace("'", "''")
	queryStr = "UPDATE responses SET qid = -1 WHERE qid = " + responseid + ";"
	executeDBCommand(conn, cur, queryStr)
	queryStr = "INSERT INTO responses VALUES (" + responseid + ", '" + responseText + "', DEFAULT, 'text', '" + influencerName + "');" 
	executeDBCommand(conn, cur, queryStr)

def updateAltCategory():
	global conn
	global cur
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	option = raw_input("Type 'c' to change a response, 'd' to delete a response, 'o' to add original to overflow if overflow doesn't exist, or 'a' to add an additional text to an overflow response (Anything else to quit): ")
	if option != 'c' and option != 'd' and option != 'o' and option != 'a':
		print 'Not a valid option\n'
		return
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	validids = []
	for row in dbdata:
		print str(row[0]) + ": " + row[1]
		validids.append(str(row[0]))
	responseid = raw_input("Input response id to change: ")
	if responseid not in validids:
		print 'Not a valid id\n'
		return
	if option == 'o':
		queryStr = "SELECT * FROM responses WHERE qid = '" + responseid + "' AND influencername = '" + influencerName + "';"
		executeDBCommand(conn, cur, queryStr)
		dbdata = cur.fetchall()
		for row in dbdata:
			queryStr = "INSERT INTO overflowresponses VALUES (" + responseid + ", '" + str(row[1]).replace("'", "''") + "', DEFAULT, '" + str(row[3]) + "', '" + influencerName + "', '" + str(row[7]) + "', DEFAULT);"
			executeDBCommand(conn, cur, queryStr)
			print 'Response succesfully moved to overflowresponses\n'
		return
	queryStr = "SELECT * FROM overflowresponses WHERE qid = '" + responseid + "' ORDER BY newid;"
	executeDBCommand(conn, cur, queryStr)
	dbdata = cur.fetchall()
	validids = []
	for row in dbdata:
		print str(row[6]) + ": " + row[1]
		validids.append(str(row[6]))
	newId = raw_input("Input alternate response id to edit/deletes: ")
	if newId not in validids:
		print 'Not a valid id'
		return
	if option == 'a':
		categoryType = raw_input("Enter 'i' for image, anything else for text: ")
		if categoryType != 'i':
			text = raw_input("Response Text (press enter to leave empty): ")
			queryStr = "INSERT INTO overflowresponses VALUES (" + responseid + ", '" + text.replace("'", "''") + "', DEFAULT, 'text', '" + influencerName + "', DEFAULT, " + newId + ");"
			executeDBCommand(conn, cur, queryStr)
		else:
			imageUrl = raw_input("Image url: ")
			imageName = raw_input("Image name: ")
			queryStr = "INSERT INTO overflowresponses VALUES (" + responseid + ", '" + imageName + "', DEFAULT, 'image', '" + influencerName + "', '" + imageUrl + "', " + newId + ");"
			executeDBCommand(conn, cur, queryStr)
		print 'Additional response added\n'
		return
	queryStr = "SELECT * FROM overflowresponses WHERE newid = '" + newId + "' ORDER BY newid;"
	executeDBCommand(conn, cur, queryStr)
	dbdata = cur.fetchall()
	validids = []
	i = len(dbdata) - 1
	for row in dbdata:
		print str(i) + ": " + row[1]
		validids.append(str(row[1]))
		i -= 1
	editId = raw_input("Input index to edit: ")
	editId = len(validids) - (1 + int(editId))
	if editId < 0 or editId >= len(validids):
		print 'Not a valid index\n'
		return
	if option == 'c':
		editStr = raw_input("Input new response: ")
		queryStr = "UPDATE overflowresponses SET response = '" + editStr.replace("'", "''") + "' WHERE response = '" + validids[editId].replace("'", "''") + "' AND newid = " + newId + ";"
		executeDBCommand(conn, cur, queryStr)
		print 'Response changed\n'
	elif option == 'd':
		queryStr = "DELETE FROM overflowresponses WHERE response = '" + validids[editId].replace("'", "''") + "' AND newid = " + newId + ";"
		executeDBCommand(conn, cur, queryStr)
		print 'Response deleted\n'

def addData():
	global conn
	global cur
	validWeights = [str(i) for i in range(5, 16)]
	userid = 'addingData'
	influencerName = promptForInfluencerName()
	if influencerName == "-1":
		return
	dbdata = getMatches(conn, cur, influencerName, 'NULL')
	validids = []
	for row in dbdata:
		print str(row[0]) + ": " + row[1]
		validids.append(str(row[0]))
	phraseid = raw_input("Input id to train: ")
	if phraseid not in validids:
		print 'Not a valid id'
		return
	while True:
		trainingPhrase = raw_input("Input phrase for category, q to quit: ")
		if trainingPhrase == 'q':
			break
		weight = raw_input("Type the weight (between 5 and 15): ")
		while weight not in validWeights:
			weight = raw_input("Type the weight (between 5 and 15): ")
		trainingPhrase = trainingPhrase.replace("'", "''")
		for i in range(0, int(weight)):
			queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '"	+ trainingPhrase + "', '" + influencerName + "', '" + userid + "', DEFAULT, 'False', 'text', 'False'," + str(phraseid) + ", DEFAULT, 100, DEFAULT, 'False');"
			executeDBCommand(conn, cur, queryStr)
	


def printOptions():
	print "0: View all messages"
	print "1: Add new category"
	print "2: Group questions"
	print "3: Recategorize Previous"
	print "4: Prompt influencer"
	print "5: Send responses to Top 5"
	print "6: Send response to single question"
	print "7: Directly text all users"
	print "8: Directly text single user"
	print "9: Input number of user to text"
	print "10: Send image to all"
	print "11: Send image to single user"
	print "12: Input number of user to send image"
	print "13: Supervise automated selections"
	print "14: Retrain model"
	print "15: Trust Model"
	print "16: Update Response"
	print "17: Text Numbers for Specific Group"
	print "18: Group New Users"
	print "19: Change Category Text"
	print "20: Add alternative response"
	print "21: Tweet"
	print "22: Add data"
	print "23: Edit/Delete/Move-to/Add overflow response"
	print "24: Send infinite\n"
	

if __name__ == '__main__':

	conn = psycopg2.connect(
        database="d1jfg4556jcg85",
        user="u95kuk1lu5e68c",
        password="p9462kijpsfllp2i03nc3bqq6gt",
        host="ec2-52-204-179-136.compute-1.amazonaws.com",
        port=5432
    )
	cur = conn.cursor()

	while True:	
		printOptions()
		category = raw_input("Enter task number (Anything else to exit): ")
		if category == "0":
			displayUnprocessedMessages()	
		elif category == "1":
			addNewCategory()
		elif category == "2":
			groupQuestions()
		elif category == "3":
			recategorizePrevious(conn, cur)
		elif category == "4":
			promptInfluencer()
		elif category == "5":
			sendResponses()
		elif category == "7":
			textAll()
		elif category == "8":
			textOne()
		elif category == "9":
			textSingleNumber()
		elif category == "10":
			sendImageToAll()
		elif category == "11":
			sendImageToOne()
		elif category == "12":
			sendImageToSingleNumber()
		elif category == "13":
			superviseAutomation()
		elif category == "14":
			retrainModel()
		elif category == "15":
			trustModel()
		elif category == "16":
			updateResponse()
		elif category == "17":
			textGroup()
		elif category == "18":
			groupNewUsers()
		elif category == "19":
			changeCategoryText()
		elif category == "20":
			addAltCategory()
		elif category == "21":
			tweet()
		elif category == "22":
			addData()
		elif category == "23":
			updateAltCategory()
		elif category == "24":
			sendInfinite()
		else:
			break

	conn.close()


