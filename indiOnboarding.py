import psycopg2

#Globals
conn = None
cur = None

def executeDBCommand(conn, cur, query):
    cur.execute(query)
    conn.commit()

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
    days = raw_input("Enter the user's workout days(MTWThFSSu): ")
    return days

def addNewUser():
    global conn
    global cur

    queryStr = "SELECT DISTINCT userID FROM unprocessedmessages WHERE influencerid = 'indibot' AND userid NOT IN (SELECT userid FROM indiuserinfo) ORDER BY userid;"
    executeDBCommand(conn, cur, queryStr)
    ids = cur.fetchall()
    validids = []
    i = len(ids) - 1
    for row in ids:
        print str(i) + ": " + row[0]
        validids.append(str(row[0]))
        i -= 1
    editId = raw_input("Input index of userId to enter: ")
    editId = len(validids) - (1 + int(editId))
    if editId < 0 or editId >= len(validids):
        print 'Not a valid index\n'
        return
    userId = validids[editId]

    queryStr = "SELECT phrase FROM unprocessedmessages WHERE userid = '" + userId + "' AND influencerid = 'indibot';"
    print '\n'
    executeDBCommand(conn, cur, queryStr)
    convo = cur.fetchall()
    for row in convo:
        print row[0]
    print '\n'
    #userId = promptForUserId()
    name = promptForName()
    gender = promptForGender()
    height = promptForHeight()
    weight = promptForWeight()
    goals = promptForGoals()
    days = promptForDays()

    queryStr = "INSERT INTO indiuserinfo VALUES (DEFAULT, '" + userId + "', '" + name + "', '" + gender + "', " + str(height) + ", " + str(weight) + ", '" + goals + "', '" +  days + "');"
    executeDBCommand(conn, cur, queryStr)

    print 'New user succesfully entered\n'

def changeUserInfo():
    global conn
    global cur

    queryStr = "SELECT DISTINCT userid FROM indiuserinfo ORDER BY userid;"
    executeDBCommand(conn, cur, queryStr)
    ids = cur.fetchall()
    validids = []
    i = len(ids) - 1
    for row in ids:
        print str(i) + ": " + row[0]
        validids.append(str(row[0]))
        i -= 1
    editId = raw_input("Input index of userId to enter: ")
    editId = len(validids) - (1 + int(editId))
    if editId < 0 or editId >= len(validids):
        print 'Not a valid index\n'
        return
    userId = validids[editId]

    queryStr = "SELECT * FROM indiuserinfo WHERE userid = '" + userId + "';"
    executeDBCommand(conn, cur, queryStr)
    users = cur.fetchall()
    if len(users) == 0:
        print '\nInvalid user ID\n'
        return

    while True:
        print "\n0: Name"
        print "1: Gender"
        print "2: Height"
        print "3: Weight"
        print "4: Goals"
        print "5: Days\n"

        option = raw_input("Select index of info you want to change ('q' to quit): ")

        if option == '0':
            name = promptForName()
            queryStr = "UPDATE indiuserinfo SET name = '" + name + "' WHERE userid = '" + userId + "';"
            break
        elif option == '1':
            gender = promptForGender()
            queryStr = "UPDATE indiuserinfo SET gender = '" + gender + "' WHERE userid = '" + userId + "';"
            break
        elif option == '2':
            height = promptForHeight()
            queryStr = "UPDATE indiuserinfo SET height = " + str(height) + " WHERE userid = '" + userId + "';"
            break
        elif option == '3':
            weight = promptForWeight()
            queryStr = "UPDATE indiuserinfo SET weight = " + str(weight) + " WHERE userid = '" + userId + "';"
            break
        elif option == '4':
            goals = promptForGoals()
            queryStr = "UPDATE indiuserinfo SET goals = '" + goals + "' WHERE userid = '" + userId + "';"
            break
        elif option == '5':
            days = promptForDays()
            queryStr = "UPDATE indiuserinfo SET days = '" + days + "' WHERE userid = '" + userId + "';"
            break
        elif option == 'q':
            return
        else:
            print 'ERROR: Invalid input, try again\n'
    executeDBCommand(conn, cur, queryStr)
    print '\nUser info succesfully changed'

def printOptions():
    print "\n0: Set-up entire new user"
    print "1: Change user's info\n"

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
        elif category == 'q':
            break
        else:
            print 'ERROR: Invalid input, try again\n'
