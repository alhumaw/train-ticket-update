import random
import json
import requests
from subprocess import getstatusoutput
import datetime



def get_ip_map():
    code,process = getstatusoutput("kubectl get svc -n train-ticket --no-headers | awk '{print $1,$3}'")
    process = process.strip().split("\n")
    full_ip_map = {}
    for services in process:
        name,ip = services.split(" ")
        name = name.replace("ts-","")
        full_ip_map[name] = ip
    port_map = {
        "admin-user-service": "16115",
        "user-service": "12340",
        "station-service": "12345",
        "travel-service": "12346",
        "preserve-service": "14568",
        "order-service": "12031",
        "route-service": "11178",
        "route-plan-service": "14578",
        "contacts-service": "12347",
        "seat-service": "18898",
        "food-map-service": "18855",
        "food-service": "18856",
        "ui-dashboard": "8080"
    }
    ip_map = {}
    for key, value in full_ip_map.items():
        if key in port_map:
            ip_map[key] = value
    print(ip_map)

    return ip_map, port_map

epoch = datetime.datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return int((dt - epoch).total_seconds() * 1000.0)

def get_random_time(upper_bound):
    current_time = datetime.datetime.now()
    bound = current_time + datetime.timedelta(days=upper_bound)
    min_millis = unix_time_millis(current_time)
    max_millis = unix_time_millis(bound)
    return random.randint(min_millis, max_millis)



class UserBase:
    def __init__(self, username, password, ip_map, port_map):
        self.username = username
        self.password = password
        self.ip_map = ip_map
        self.port_map = port_map

    def get_addr(self, service, path):
        return 'http://' + self.ip_map[service] + ':' + self.port_map[service] + path

    def auth_headers(self):
        return {'Authorization': 'Bearer ' + self.token}

    def login(self):
        response = requests.post(self.get_addr('ui-dashboard', "/api/v1/users/login"),
                                 json={'username':self.username, 'password': self.password, 'verificationCode':'1234'})
        data = json.loads(response._content)['data']
        self.token = data['token']
        self.userId = data['userId']
