import mysql.connector  # import the mysql connector python library

connection = mysql.connector.connect(host="localhost", user="root", password="",
                                     database="crud")  # initializing connection with mysql database
my_cursor = connection.cursor()  # create object to perform Query operation in mysql db


def connection_check():
    if connection.is_connected():
        print("Connection Successfully ")
    else:
        print("Connection Failed")


# check connectivity with database
connection_check()
table_name = "student_details"


# create table to store user details
def create_table():
    # create a table in database
    my_cursor.execute(
        f"create table {table_name}(id INT AUTO_INCREMENT,RollNo INT , FullName VARCHAR(30) , Marks INT,PRIMARY KEY(id))")


# create operation in database
def create_data():
    name = str(input("Enter your Full Name :"))
    roll = int(input("Enter Roll No :"))
    marks = int(input("Enter Marks :"))
    try:
        my_cursor.execute(f"INSERT INTO {table_name}(FullName, RollNo,Marks) values('{name}',{roll},{marks})")
        connection.commit()
        return print("Record is Inserted Successfully")
    except:
        print("Error in the create_data()")
        connection.rollback()


# traversing in database
def read_data():
    try:
        my_cursor.execute(f"select * from {table_name}")
        result = my_cursor.fetchall()
        if len(result) == 0:
            print("No Records Found")
        else:
            for i in result:
                id_no = i[0]
                roll = i[1]
                name = i[2]
                marks = i[3]
                print(f"Record ID No = {id_no}, Full Name = {name}, Roll No = {roll}, Marks = {marks},")

    except:
        print(" Error in the read_data()")


# update operation in database
def update_data():
    up_choice = int(input('''Select option:
1. Update Full Name
2. Update roll no
3. Update marks
4. Main menu
Input :'''))
    if up_choice == 1:
        id_no = int(input("Enter ID No :"))
        name = str(input("Updated Full Name :"))
        try:
            my_cursor.execute(f"update {table_name} set FullName = '{name}'  where id = {id_no} ;")
            connection.commit()
            print("Record is updated Successfully")
        except:

            print("Record not found")
    elif up_choice == 2:
        id_no = int(input("Enter ID No :"))
        roll = int(input("Updated Roll No :"))
        try:
            my_cursor.execute(f"update {table_name} set RollNo = {roll}  where id = {id_no} ;")

            connection.commit()
            print("Record is updated Successfully")
        except:
            print("Record not found")
    elif up_choice == 3:
        id_no = int(input("Enter ID No :"))
        marks = int(input("Updated Marks :"))
        try:
            my_cursor.execute(f"update {table_name} set Marks = {marks}  where id = {id_no} ;")
            connection.commit()
            print("Record is updated Successfully")
        except:
            print("Record not found")
    elif up_choice == 4:
        return
    else:
        print("Invalid choice")


# delete operation in database
def delete_data():
    choice = int(input('''
Select option:
1. delete Record 
2. delete All Records
4. Main menu
Input :'''))
    if choice == 1:
        id_no = int(input("Enter ID No :"))
        try:
            my_cursor.execute(f"delete from studentData where id = {id_no};")
            connection.commit()
            print("Record is deleted Successfully")
        except:
            print(f"ID No = {id_no} not found in student Table")
    elif choice == 2:
        try:
            my_cursor.execute(f"TRUNCATE TABLE {table_name} ")
            # my_cursor.execute(f"DELETE FROM {table_name} ")
            connection.commit()
            print("All Records is being deleted Successfully")
        except:
            print("invalid command")
    elif choice == 4:
        return
    else:
        print("  Invalid choice")


# create read update and delete operation on database
def crud():
    select = 0
    while select != 5:
        # print("hello ")
        select = int(input('''

Select option:
1. create
2. read
3. update
4. delete 
5. exit
Input :'''))
        if select == 1:
            create_data()
            # print('Create')
        elif select == 2:
            read_data()
            # print('Read')
        elif select == 3:
            update_data()
            # print('Read')
        elif select == 4:
            delete_data()
            # print('Read')
        elif select == 5:
            print("Exiting ...")
            break
        else:
            print("Invalid choice")


# create_table()
crud()

connection.close()
