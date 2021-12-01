import mysql.connector
from datetime import datetime
db = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'nawaf123',
    database = 'attendance'
)

cursor = db.cursor()
now = datetime.now()
date = now.strftime("%b-%d-%y")
name = "nawaf"
print(date)
#cursor.execute("create table Attendace(Name varchar(20) not null,Time datetime not null)")
#cursor.execute("alter table Attendace change Time Time varchar(10)")

time = now.strftime("%H-%M-%S")
#cursor.execute("insert into Attendace(Name,Time,Date) values (%s,%s,%s)",(name,time,date))
#db.commit()
#cursor.execute("SELECT EXISTS(SELECT Name FROM Attendace where Name = 'nawaf')")
cursor.execute("SELECT * from Attendace")
for d in cursor:
    print(d)




