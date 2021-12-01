
import cv2
import numpy as np 
import face_recognition
import os
import pickle

import mysql.connector
from datetime import datetime,timedelta

#Connecting with mysql database :)
#enter your own mysql auth credentials or else will be met with an error
db = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'nawaf123',
    database = 'attendance'
)
#loading my trained model to distinguish beteen similar face and same face
loaded_model = pickle.load(open('finalized_model.sav', 'rb'))

#connected database object
cursor = db.cursor()

#path where the images of registered faces are residing
path = "registeredFaces"

#get a list of all names(registered person's name) of images residing in registeredFaces
dirlist = os.listdir(path)
images = []
registered_names = []

for file_name in dirlist:
    image = cv2.imread(f"{path}/{file_name}")

    #Appending the image(pixel values) in registered faces to list
    images.append(image)

    #removing the .jpg extension form the image name to get the persons name
    name = os.path.splitext(file_name)[0]
    registered_names.append(name)


#A function to check if the recognized face of a registered person form the webcam is already marked as present
def IfAdded(name,check_if_recently_added = False):
    now = datetime.now()
    date = now.strftime("%b-%d-%y")
    
    #checking in the databse wthere the name has been marked as present for the present date, return 0 or 1 
    cursor.execute("SELECT EXISTS(SELECT Name FROM Attendace WHERE Date = (%s) and Name = (%s))",(date,name))
    
    

    for data in cursor:
        if not check_if_recently_added: 
            
            return data[0]
        else:
            
            if data[0]:
                #check if added very recentlly,if yes then we can prevent the output frok fluctuating from name Nd unregistered
                cursor.execute("SELECT last_checked FROM Attendace WHERE Date = (%s) and Name = (%s)",(date,name))
                
                for update_time in cursor:
                    now = now.strftime("%H-%M-%S")
                    now = datetime.strptime(now, "%H-%M-%S")

                    #as model confidance threshold to mark a name as recognised and marked is given high to improve accuracy,hence chances
                    #are the registered face might be shown as unregistered for few sec.
                    #To mitigate this issue, if the name has already been recognised with good confidance within a 10 sec margin 
                    #chances are we'r poiting at the same user....
                    #hence to prevent
                    #from fluctuating from name Nd unregistered tag we check if the name is recently added  withing 10 sec and 
                    #display the name if recently added and our encodings is persuing it to be that person eventhough with low confidance. 
                    return now <= datetime.strptime(update_time[0], "%H-%M-%S")+timedelta(seconds=10)
            else:
                return False
                        
        
#function to return the image encodings ie an array of 128 unique measurnments
def findEncodings(images):
    registered_face_enc = []
    for img in images:
        #convert from BGR to RGB format
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        emb = face_recognition.face_encodings(img)[0]
        
        registered_face_enc.append(emb)
    return registered_face_enc

#function to add the recognised name to the database or to update when ws it last checked
def addEntity(name,update_last_checked = False):
    now = datetime.now()
    date = now.strftime("%b-%d-%y")
    last_checked = now.strftime("%H-%M-%S")
    
    
    if not update_last_checked:
        
        cursor.execute("insert into Attendace(Name,Time,Date,last_checked) values (%s,%s,%s,%s)",(name,last_checked,date,last_checked))
    else:
        print("updatinggg")
        print("unserting-",last_checked)
        cursor.execute("UPDATE Attendace SET last_checked=(%s) WHERE Name=(%s) and Date = (%s);",(last_checked,name,date))

    #commit the changes made to the database
    db.commit()


registered_face_enc = findEncodings(images)

cam = cv2.VideoCapture(0)

while True:
    #read each frame from the webcam
    scuccess,frame = cam.read()

    #resize the frame to its 1/4th size
    imageS = cv2.resize(frame,(0,0),None,0.25,0.25)

    imageS = cv2.cvtColor(imageS,cv2.COLOR_BGR2RGB)
    
    #detect all the locations of face in the frame
    face_locations = face_recognition.face_locations(imageS)

    #get the the face encodings of all the faces in the frame
    face_embeddings = face_recognition.face_encodings(imageS,face_locations)
    
    #itterating through each of the face locations and its respective encoding
    for location,encoding in zip(face_locations,face_embeddings):

        #checking if the face encodings among the registered faces has macth with the face encoding form the frame
        match = face_recognition.compare_faces(registered_face_enc,encoding)

        #getting the ecoding distance of the face encoding from the frame with easch of the encodings in the registered face
        enc_dist = face_recognition.face_distance(registered_face_enc,encoding)
        
        #get the the registered face index with which the frame face encoding is closest with
        match_index = np.argmin(enc_dist)
        
        #if the closest encoding with the registered face is a match 
        if match[match_index]:
            reg_enc = registered_face_enc[match_index]
            #resize the encoding to shape (1,128)
            reg_enc = reg_enc.reshape(1,-1)
            encoding = encoding.reshape(1,-1)
            
            #concatenate the matched registered face enc and the frame face encoding to be given as an input to similar face enc distinguiher model
            data = np.concatenate((encoding,reg_enc),axis=1)

            #predicting if the matched frame face encoding is actually a proper match to the correct registered face or it matched with a similar registered face
            #this step is crucial as often time without this step,a registered face with very similar face measurnment to the frame face enc is matched...
            #this step ensurs high accuracy and robustness...
            prediction = loaded_model.predict_proba(data)[:,1]
            
            name = registered_names[match_index]

            #through auc curve it was discovered that 61 is the best threshold to ditinguish between both class
            if prediction*100 > 60.0:
                
                #check if allready marked in database,if not then add in database
                #if already  added then update the last_checked parameter
                if IfAdded(name):
                    
                    addEntity(name,update_last_checked = True)
                    name = f"{name}+Marked"
                else:
                    
                    addEntity(name)
                    name = f"{name}+Marked"
            #if model not confidant that the person has registered,then check if the person has been recently added in 10 sec
            #if yes chances are the person in veiw is same person and is registered
            #if all above conditions fail the person is not resgistered
            else:

                if  IfAdded(name,check_if_recently_added=True):      
                    name = f"{name}+Marked"
                else:
                    name = "Not registered"
            
            #put text at the location of the face in the frame
            x1,x2,y2,y1 = location
            x1,x2,y2,y1 = x1*4,x2*4,y2*4,y1*4
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.rectangle(frame,(x1,y2-35),(x2,y2),(0,255,0),cv2.FILLED)
            cv2.putText(frame,name,(x1+6,y2-6),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2)

    #display webcam feed
    cv2.imshow("webcame",frame)
    cv2.waitKey(1)

