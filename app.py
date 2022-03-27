from flask import Flask,request
from flask import render_template, Response,session,redirect,url_for
from PIL import Image 
import os
import mysql.connector
import attendance
import cv2
import numpy as np
import ast
import re
import datetime
camera = cv2.VideoCapture(0)
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r"/home/nawaf/Projects/FacialRecognizationAttendance/registeredFaces"
app.secret_key = '990199'
db = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'nawaf123',
    database = 'attendance',
    autocommit=True
)


#connected database object
cursor = db.cursor(dictionary = True)

def gen_frames(SubID,pno):  
    print("hereeeeee")
    names = []
    encodings = []
    usn = []
    cursor.execute("select * from Students")
    all = cursor.fetchall()
    print("fetched")
    if not all:
        return "no students have been registered"
    
    for data in all:
        
        names.append(data['NAME'])
        usn.append(data['USN'])
        
        encodings.append(np.array(ast.literal_eval(data['Encodings'])))
    print("pppppppppp")
    while True:
        print("pop")
        success, frame = camera.read()
        print("yes")  # read the camera frame
        if not success:
            break
        else:
            
            
            frame = attendance.Start(SubID,frame,names,usn,encodings,pno)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/HomePage')
def HomePage():
    msg = f"Welcome {session['username']}!"
    return render_template("index.html",msg = msg)

@app.route("/login",methods = ["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html",msg = '')
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        
        cursor.execute('SELECT * FROM Proffessors WHERE Proff_name = (%s) AND Password = (%s)', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account["proff_id"]
            session['username'] = account["proff_name"]
            # Redirect to home page
            
            return redirect(url_for("HomePage"))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
            return render_template("login.html",msg = msg)

@app.route("/register",methods = ["GET","POST"])
def registerTeacher():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        id = request.form['id']
        mobile = request.form['mobile']
        cursor.execute('SELECT * FROM Proffessors WHERE proff_id= (%s)', (id,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Username already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO Proffessors VALUES (%s, %s, %s, %s, %s)', (id,username,mobile,email,password))
            db.commit()
           
        # Fetch one record and return result
            
            
            session['loggedin'] = True
            session['id'] = id
            session['username'] = username
            msg = f"Welcome {username}!"
            
            return render_template("index.html",msg = msg)

        return render_template("register.html",msg = msg)

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
        # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/TakeAttendance',methods = ["GET","POST"])
def TakeAttendance():
        if session['loggedin']:
            return render_template("takeAttendance.html",msg = '')
        else:
            return render_template("login.html",msg = "please login or register first")

@app.route('/cam',methods = ["GET","POST"])
def cam():

    pno = str(request.form["pno"])
    sem = str(request.form["sem"])
    proff_id = session["id"]
    cursor.execute("Select * from subsTaken where proff_id = (%s) and SEM = (%s)",(proff_id,sem))
    sub = cursor.fetchone()
    if not sub:
        return render_template("takeAttendance.html",msg = "You don't take class for the selected semester")
    return Response(gen_frames(sub["subId"],pno), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))


@app.route('/RegisterStudent',methods = ["GET","POST"])
def RegisterStudent():
    
    if (request.method == "GET"):
        
        return render_template("Register.html")
    else:
        name = request.form["Name"]
        USN = request.form["USN"]
        Number = request.form["Number"]
        SEM = request.form["SEM"]
        Branch = request.form["Branch"]

        f = request.files['image']  
        filename = name+"-"+USN
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename)) 
        #attendance.storeAllEmbeddings()
        attendance.storeStudent(filename,USN,SEM,name,Number,Branch)
        
        return render_template("Register.html")

def getTodaysRecords(proff_id,status,date = "today"):
    if date == "today":
        today = datetime.date.today()
        date = today.strftime("%b-%d-%y")
    else:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%b-%d-%y")
        
    records = []
    sems = []
    subjects = []
    subIds = []
    totalperiod = []
    cursor = db.cursor(dictionary = True)
    for sem in range(1,9):
        
        cursor.execute("Select * from subsTaken where proff_id = (%s) and SEM = (%s)",(proff_id,sem))
        subject = cursor.fetchone()
        
        if subject:
        
            cursor.execute("Select * from SubjectsSem where subId = (%s)",(subject["subId"],))
            
            subname = cursor.fetchone()
    
            if subname:
                
                subIds.append(subname["subId"])
                sems.append(sem)
                subjects.append(subname["subName"])
    
    for SubID in subIds:
        periods = 0
        for periodNo in range(1,7):
        
            if status == "present":
                clause = "Select * from Attendance where periodNo = %s and subId = %s and Date = %s"
                cursor.execute(clause,(periodNo,SubID,date))
                students = cursor.fetchall()
            else:
                clause = "Select * from Attendance where periodNo = %s and subId = %s and Date = %s"
                cursor.execute(clause,(periodNo,SubID,date))
                students = cursor.fetchall()
                clause = "select USN,NAME,MOBILE from Students where USN not in  (select USN from Attendance where periodNo = %s and subId = %s and Date = %s)"
                cursor.execute(clause,(periodNo,SubID,date))
                rec = cursor.fetchall()
            
            
            
            if students:
        
                print(records)
                periods += 1
                if status == "absent":
                    records.append(rec)
                records.append(students)
        
        totalperiod.append(periods)
    #print(periods,records)
    print(totalperiod)
    return totalperiod,records,subjects,sems

@app.route("/attendanceTable",methods = ["GET","POST"])
def attendanceTable():
    print("acted")
    proff_id = session['id']
    if request.method == "GET":
        status = "present"
        totalperiod,records,subjects,sems = getTodaysRecords(proff_id,status = "present")
        date = datetime.date.today()
    else:
        
        status = request.form["status"]
        
        date = request.form['date']
        print("fg",date)
        if not date:
            print("yes")
            date = "today"
        totalperiod,records,subjects,sems = getTodaysRecords(proff_id,status = status,date = date)
    
    return render_template("table.html",periods = totalperiod,records = records,subject_name = subjects,SEM = sems,status = status,date = date)
if __name__ == "__main__":
    app.run(debug = True)