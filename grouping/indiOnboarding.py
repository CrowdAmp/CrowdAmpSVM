import psycopg2
from flask import Flask, jsonify, request, json
import requests

#Globals
conn = None
cur = None

def executeDBCommand(conn, cur, query):
    cur.execute(query)
    conn.commit()

def maleForm(cardio, age, time, weight):
    if cardio:
        return ((age * 0.2017) - (weight * 0.09036) + (150 * 0.6309) - 55.0969) * time / 4.184
    else:
        return ((age * 0.2017) - (weight * 0.09036) + (100 * 0.6309) - 55.0969) * time / 4.184
        
def femaleForm(cardio, age, time, weight):
    if cardio:
        return ((age * 0.074) - (weight * 0.05741) + (150 * 0.4472) - 20.4022) * time / 4.184
    else:
        return ((age * 0.074) - (weight * 0.05741) + (100 * 0.4472) - 20.4022) * time / 4.184

def calorieForm(age, height, weight, male):
    if male:
        calories = (10 * weight) + (6.25 * (height * 2.54)) - (5 * age) + 5
    else:
        calories = (10 * weight) + (6.25 * (height * 2.54)) - (5 * age) - 161
    return calories

def promptForUserId():
    global conn
    global cur
    queryStr = "SELECT DISTINCT userid, name FROM indiuserinfo ORDER BY userid;"
    executeDBCommand(conn, cur, queryStr)
    ids = cur.fetchall()
    validids = []
    i = len(ids) - 1
    for row in ids:
        print str(i) + ": " + row[0] + " | " + row[1]
        validids.append(str(row[0]))
        i -= 1
    editId = raw_input("Input index of userId to enter: ")
    editId = len(validids) - (1 + int(editId))
    if editId < 0 or editId >= len(validids):
        print 'Not a valid index\n'
        return
    return validids[editId]


def promptForName():
    name = raw_input("Enter the new user's name: ")
    return name

def promptForGender():
    gender = raw_input("Enter the new user's gender(M or F): ")
    if gender == 'M' or gender == 'm':
        gender = 'm'
    elif gender == 'F' or gender =='f':
        gender = 'f'
    else:
        print 'ERROR: Invalid input, try again\n'
        return promptForGender()
    return gender

def promptForAge():
    age = raw_input("Enter the age of the user: ")
    return age

def promptForHeight():
    feet = raw_input("Enter how many feet tall the user is: ")
    inches = raw_input("Enter the inches: ")
    height = (int(feet) * 12) + int(inches)
    return height

def promptForWeight():
    weight = raw_input("Enter the user's weight (lbs): ")
    return weight

def promptForGoals():
    goals = raw_input("Enter the user's goals: ")
    return goals

def promptForDays():
    days = raw_input("Enter the user's workout days(MTuWThFSaSu): ")
    return days

def addNewUser():
    global conn
    global cur
    queryStr = "SELECT DISTINCT userid FROM unprocessedmessages WHERE influencerid = 'indibot' AND userid NOT IN (SELECT userid FROM indiuserinfo) ORDER BY userid;"
    executeDBCommand(conn, cur, queryStr)
    ids = cur.fetchall()
    validids = []
    i = len(ids) - 1
    for row in ids:
        print str(i) + ": " + row[0]
        validids.append(str(row[0]))
        i -= 1
    editId = raw_input("Input index of the user's user ID to add: ")
    editId = len(validids) - (1 + int(editId))
    if editId < 0 or editId >= len(validids):
        print 'Not a valid index\n'
        return
    userId = validids[editId]

    queryStr = "SELECT phrase FROM unprocessedmessages WHERE userid = '" + userId + "' AND influencerid = 'indibot' ORDER BY timesent;"
    executeDBCommand(conn, cur, queryStr)
    convo = cur.fetchall()
    print '\n'
    for row in convo:
        print row[0]
    print '\n'
    name = promptForName()
    gender = promptForGender()
    age = promptForAge()
    height = promptForHeight()
    weight = promptForWeight()
    goals = promptForGoals()
    days = promptForDays()

    queryStr = "INSERT INTO indiuserinfo VALUES (DEFAULT, '" + userId + "', '" + name + "', '" + gender + "', " + str(age) + ", " + str(height) + ", " + str(weight) + ", '" + goals + "', '" +  days + "');"
    executeDBCommand(conn, cur, queryStr)

    print 'New user succesfully entered\n'

def changeUserInfo():
    global conn
    global cur

    userId = promptForUserId()

    queryStr = "SELECT * FROM indiuserinfo WHERE userid = '" + userId + "';"
    executeDBCommand(conn, cur, queryStr)
    users = cur.fetchall()
    if len(users) == 0:
        print '\nInvalid user ID\n'
        return

    while True:
        print "\n0: Name"
        print "1: Gender"
        print "2: Age"
        print "3: Height"
        print "4: Weight"
        print "5: Goals"
        print "6: Days\n"

        option = raw_input("Select index of user info you want to change ('q' to quit): ")

        if option == '0':
            name = promptForName()
            queryStr = "UPDATE indiuserinfo SET name = '" + name + "' WHERE userid = '" + userId + "';"
            break
        elif option == '1':
            gender = promptForGender()
            queryStr = "UPDATE indiuserinfo SET gender = '" + gender + "' WHERE userid = '" + userId + "';"
            break
        elif option == '2':
            age = promptForAge()
            queryStr = "UPDATE indiuserinfo SET age = " + str(age) + " WHERE userid = '" + userId + "';"
            break
        elif option == '3':
            height = promptForHeight()
            queryStr = "UPDATE indiuserinfo SET height = " + str(height) + " WHERE userid = '" + userId + "';"
            break
        elif option == '4':
            weight = promptForWeight()
            queryStr = "UPDATE indiuserinfo SET weight = " + str(weight) + " WHERE userid = '" + userId + "';"
            break
        elif option == '5':
            goals = promptForGoals()
            queryStr = "UPDATE indiuserinfo SET goals = '" + goals + "' WHERE userid = '" + userId + "';"
            break
        elif option == '6':
            days = promptForDays()
            queryStr = "UPDATE indiuserinfo SET days = '" + days + "' WHERE userid = '" + userId + "';"
            break
        elif option == 'q':
            return
        else:
            print 'ERROR: Invalid input, try again\n'
    executeDBCommand(conn, cur, queryStr)
    print '\nUser info succesfully changed'

def sendDaily():
    global conn
    global cur
    day = raw_input("Enter today's date (MTuWThFSaSu): ")
    if day not in 'MTuWThFSaSu' or day == '':
        print 'ERROR: Not a valid day'
        return
    queryStr = "SELECT DISTINCT * FROM indiuserinfo;"
    executeDBCommand(conn, cur, queryStr)
    users = cur.fetchall()
    validUsers = []
    for user in users:
        if day in user[8]:
            validUsers.append(str(user[1]))
    print 'Sending to:', validUsers
    message = raw_input("Enter message to send ('d' for default): ")
    if message == 'd':
        message = 'Today is a gym day! Let me know when you workout so that I can log it in for you.'
    message = message.replace("'", "''")
    for user in validUsers:
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)
    print 'Successfully sent reminders\n'

def sendErr():
    global conn
    global cur

    f = open('prem.txt', 'r')

    for user in f:
        user = str(user)
        message = "Hey, I am really sorry that I have not been able to answer all of your messages. Unfortunately, I am having some technical difficulties. :("
        message = message.replace("'", "''")
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)

        message = "I am working very hard to get everything working, and I should be up and running again on two or three weeks."
        message = message.replace("'", "''")
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)

        message = "I feel really bad about this trouble, so to make it up to you, once I am up and running again, I am going to give you Indi Pro free for life! :D"
        message = message.replace("'", "''")
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)

        message = "All you have to do is send me your email, and follow the instructions on this webpage to unsubscribe from apple payments. http://tinyurl.com/IndiUnsubscribe"
        message = message.replace("'", "''")
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)

        message = "I will remember you, and once I am working again, I will send you a message so we can get started on your fitness goals!"
        message = message.replace("'", "''")
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : user, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + user + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)

def addInfo():
    global conn
    global cur 

    userId = promptForUserId()

    option = raw_input("Enter if the user entered food or exercise [f/e]: ")
    if option == 'f':
        option = 'food'
        calories = raw_input("Enter the number of calories the meal contains: ")
        comment = raw_input("Enter the food consumed: ")
        day = raw_input("Enter the day of the week (MTuWThFSaSu): ")
        queryStr = "INSERT INTO indilog VALUES (DEFAULT, '" + userId + "', '" + option + "', " + str(int(calories)) + ", '" + comment + "', DEFAULT, FALSE, '" + day + "', DEFAULT);"
        executeDBCommand(conn, cur, queryStr)
        print 'Exercise/food added\n'
        message = "Thank you for updating me! I have added " + str(int(calories)) + " calories for your " + comment + " for today!"
    elif option == 'e':
        option = 'exercise'
        comment = raw_input("Enter the exercise performed: ")
        day = raw_input("Enter the day of the week (MTuWThFSaSu): ")
        time = raw_input("Enter time spent on the exercise: ")
        cardio = raw_input("Cardio or weight training (c/w): ")
        custom = raw_input("Enter custom calorie or forumula (c/f): ")
        queryStr = "SELECT age, weight, gender FROM indiuserinfo WHERE userid = '" + userId + "';"
        executeDBCommand(conn, cur, queryStr)
        userInfo = (cur.fetchall())[0]
        print userInfo
        if cardio == 'c':
            cardio = True
        elif cardio == 'w':
            cardio = False
        else:
            print 'ERROR: Invalid option\n'
            return
        if userInfo[2] == 'm':
            calories = maleForm(cardio, float(userInfo[0]), float(time), float(userInfo[1]))
        elif userInfo[2] == 'f':
            calories = femaleForm(cardio, float(userInfo[0]), float(time), float(userInfo[1]))
        if custom == 'c':
            calories = raw_input("Enter calories burned on workout: ")
        queryStr = "INSERT INTO indilog VALUES (DEFAULT, '" + userId + "', '" + option + "', " + str(calories) + ", '" + comment + "', " + time + ", FALSE, '" + day + "', DEFAULT);"
        executeDBCommand(conn, cur, queryStr)
        print 'Exercise/food added\n'
        message = "Based on your weight and how long you exercised, I will input " + str(int(calories)) + " calories burned during your workout! Great job!" 
    else:
        print 'ERROR: Invalid option\n'
        return

    sendMessage = raw_input("Send the message to the user? (y/n): ")
    if sendMessage == 'y':
        data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : userId, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)
        queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + userId + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
        executeDBCommand(conn, cur, queryStr)
        print 'Food message sent'

def sendCal():
    global conn
    global cur 
    
    userId = promptForUserId()
    calories = raw_input("Enter the number of calories consumed: ")
    message = "Awesome! I have logged " + str(int(calories)) + " calories!"

    data = { "content" : message, "influencerId" : "indibot", "type": "text", "userId" : userId, "mediaDownloadUrl" : ""}
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(data), headers=headers)

    queryStr = "INSERT INTO unprocessedmessages VALUES (DEFAULT, '" + message + "', 'indibot', '" + userId + "', DEFAULT, 'False', 'text', 'False', DEFAULT, DEFAULT, DEFAULT, DEFAULT, 'False');"
    executeDBCommand(conn, cur, queryStr)
    
    print 'Calorie message sent'

def calcCalories():
    userId = promptForUserId()

def printOptions():
    print "\n0: Set-up an entire new user"
    print "1: Change existing user's information"
    print "2: Send daily reminder for a specific day"
    print "3: Add exercise or food for a user"
    print "4: I have added x calories\n"

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
        category = raw_input("Enter task number ('q' to quit): ")
        if category == '0':
            addNewUser()
        elif category == '1':
            changeUserInfo()
        elif category == '2':
            sendDaily()
        elif category == '3':
            addInfo()
        elif category == '4':
            sendCal()
        elif category == '7':
            sendErr()
        elif category == 'q':
            break
        else:
            print 'ERROR: Invalid input, try again\n'
