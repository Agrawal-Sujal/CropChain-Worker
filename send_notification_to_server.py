import requests


def sendNotification(aadhar_id,title ,body,imageId,imageType):
    url = "https://cropchain-backend-9b3l.onrender.com/fcm/sendNotification/"  
    payload = {
        "aadhar_id": aadhar_id,
        "title": title,
        "body": body,
        "imageId":str(imageId),
        "imageType": str(imageType)
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print("Status Code:", response.status_code)
    print("Response:", response.json())
