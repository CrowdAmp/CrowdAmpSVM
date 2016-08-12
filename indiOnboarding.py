import psycopg2

def promptForName():
	name = raw_input("Enter the new user's name: ")
	return name

def promptForGender():
	gender = raw_input("Enter the new user's gender(M or F): ")
	if gender == 'M' or gender == 'm':
		gender = 'male'
	elif gender == 'F' or gender =='f':
		gender = 'female'
	else:
		print 'ERROR: Invalid input, try again\n'
		return promptForGender()
	return gender

def promptForHeight():
	feet = raw_input("Enter how many feet tall the user is: ")
	inches = raw_input("Enter the inches: ")
	height = (feet * 12) + inches
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

def changeUserInfo():
	user = raw_input("Enter user you want to change: ")
		#TODO: User check

	while True:
		print "0: Name"
		print "1: Gender"
		print "2: Height"
		print "3: Weight"
		print "4: Goals"
		print "5: Days\n"

		option = raw_input("Select index of info you want to change: ")

		if option == '0':
			name = promptForName()
			continue
		elif option == '1':
			gender = promptForGender()
			continue
		elif option == '2':
			height = promptForHeight()
			continue
		elif option == '3':
			weight = promptForWeight()
			continue
		elif option == '4':
			goals = promptForGoals()
			continue
		elif option == '5':
			days = promptForDays()
			continue
		else:
			print 'ERROR: Invalid input, try again\n'

def printOptions():
	print "0: Set-up entire new user"
	print "1: Change user's info\n"

while True:
	printOptions()
	category = raw_input("Enter task number ('q' to exit): ")
	if category == '0':
		name = promptForName()
		gender = promptForGender()
		height = promptForHeight()
		weight = promptForWeight()
		goals = promptForGoals()
		days = promptForDays()
		#TODO: Push to db
	elif category == '1':
		changeUserInfo()
	elif category == 'q':
		break
	else:
		print 'ERROR: Invalid input, try again\n'