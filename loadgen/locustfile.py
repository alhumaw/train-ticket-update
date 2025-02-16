import uuid
import json
import random
import time
from locust import HttpUser, task, between
from kube import get_ip_map, UserBase, get_random_time

class NormalUser(HttpUser):
    host = "http://10.102.65.26:32677"
    weight = 100
    wait_time = between(1, 2.5)

    ip_map, port_map = get_ip_map()

    def on_start(self):
        username = 'fdse_microservice'
        password = '111111'
        self.login(username, password)

    def get_addr(self, service, path):
        return 'http://' + NormalUser.ip_map[service] + ':' + NormalUser.port_map[service] + path

    def auth_headers(self):
        return {'Authorization': 'Bearer ' + self.token}

    def login(self, username, password):
        url = self.get_addr('ui-dashboard', "/api/v1/users/login")
        payload = {'username': username, 'password': password, 'verificationCode': '1234'}
        print(f"[DEBUG] Logging in with URL: {url} and payload: {payload}")
        response = self.client.post(url, json=payload)
        print(f"[DEBUG] Login response status: {response.status_code}")
        try:
            resp_json = json.loads(response._content.decode('utf-8'))
            print(f"[DEBUG] Login response JSON: {resp_json}")
        except Exception as e:
            print(f"[ERROR] Failed to parse JSON response: {e}")
            resp_json = {}
        data = resp_json.get('data')
        if not data:
            print(f"[ERROR] Login failed, no data in response. Full response: {response._content.decode('utf-8')}")
            # Optionally, you can set a default token or exit
            return
        self.token = data.get('token')
        self.userId = data.get('userId')
        print(f"[DEBUG] Login successful. Token: {self.token}, UserID: {self.userId}")



    def getAllTrips(self):
        response = self.client.get(self.get_addr('travel-service', "/api/v1/travelservice/trips"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def getAllStations(self):
        response = self.client.get(self.get_addr('station-service', "/api/v1/stationservice/stations"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def getAllContacts(self):
        response = self.client.get(self.get_addr('contacts-service', "/api/v1/contactservice/contacts"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def getAllRoutes(self):
        response = self.client.get(self.get_addr('route-service', "/api/v1/routeservice/routes"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def choose_two(self, l):
        return random.sample(l, 2)

    def get_route_from_trip(self, trip):
       response = self.client.get(self.get_addr('route-service', "/api/v1/routeservice/routes/" + trip['routeId']),
                               headers=self.auth_headers())
       return json.loads(response._content)['data']

    def getAllOrders(self):
       response = self.client.get(self.get_addr('order-service', "/api/v1/orderservice/order"),
                                headers=self.auth_headers())
       return json.loads(response._content)['data']

    def get_food_for_trip(self, trip_date_time, start, end, tripId):
        response = self.client.get(self.get_addr('food-service', "/api/v1/foodservice/foods/%s/%s/%s/%s" %
                                              (trip_date_time, start, end, tripId)),
                                headers=self.auth_headers())
        return json.loads(response._content)['data']

    def get_a_trip_between_stations(self, start, end, trip_date):
        ret_trip = {}
        if random.choice([0, 1]) == 0:
            response = self.client.post(self.get_addr('route-plan-service', "/api/v1/routeplanservice/routePlan/" +
                                                   random.choice(['cheapestRoute', 'quickestRoute', 'minStopStations'])),
                                     json = {
                                         "formStationName": start,
                                         "toStationName": end,
                                         "travelDate": trip_date
                                     },
                                     headers=self.auth_headers())
            trips = json.loads(response._content)['data']
            if len(trips) == 0: return None
            trip = random.choice(trips)
            ret_trip['tripId'] = trip['tripId']
            ret_trip['startingStation'] = trip['fromStationName']
            ret_trip['terminalStation'] = trip['toStationName']
        else:
            response = self.client.post(self.get_addr('travel-service', "/api/v1/travelservice/trips/left"),
                                     json = {
                                         "startingPlace": start,
                                         "endPlace": end,
                                         "departureTime": trip_date
                                     },
                                     headers=self.auth_headers())
            trips = json.loads(response._content)['data']
            if len(trips) == 0: return None
            trip = random.choice(trips)
            ret_trip['tripId'] = trip['tripId']['type'] + trip['tripId']['number']
            ret_trip['startingStation'] = trip['startingStation']
            ret_trip['terminalStation'] = trip['terminalStation']
        return ret_trip

    @task
    def query_orders(self):
        choice = random.choice([0, 1, 2])
        if choice == 0:
            start_travel_date = get_random_time(100)
            end_travel_date = start_travel_date + 84000*random.randint(10, 100)*1000
            response = self.client.post(self.get_addr('order-service', "/api/v1/orderservice/order/query"),
                                     json = {
                                         "loginId": self.userId,
                                         "enableTravelDateQuery": True,
                                         "boughtDateStart": start_travel_date,
                                         "travelDateEnd": end_travel_date
                                     }, headers=self.auth_headers())
        elif choice == 1:
            response = self.client.post(self.get_addr('order-service', "/api/v1/orderservice/order/query"),
                                     json = {
                                         "loginId": self.userId,
                                         "enableStateQuery": True,
                                         "state": random.choice([0, 1])
                                     }, headers=self.auth_headers())
        else:
            start_travel_date = get_random_time(100)
            end_travel_date = start_travel_date + 84000*random.randint(10, 100)*1000
            response = self.client.post(self.get_addr('order-service', "/api/v1/orderservice/order/query"),
                                     json = {
                                         "loginId": self.userId,
                                         "enableBoughtDateQuery": True,
                                         "boughtDateStart": start_travel_date,
                                         "boughtDateEnd": end_travel_date
                                     }, headers=self.auth_headers())

    @task
    def get_sold_tickets(self):
        try:
            orders = self.getAllOrders()
            print("[DEBUG] Orders returned:", orders)
            random_order = random.choice(orders)
        except Exception as e:
            print("[ERROR] Failed to get orders or select a random order:", e)
            return

        travel_date = random_order.get('travelDate')
        train_number = random_order.get('trainNumber')
        url = self.get_addr('order-service', "/api/v1/orderservice/order/tickets")
        payload = {
            "travelDate": travel_date,
            "trainNumber": train_number
        }
        print(f"[DEBUG] Sending POST to {url} with payload: {payload}")
        
        response = self.client.post(url, json=payload, headers=self.auth_headers())
        print(f"[DEBUG] Response status code: {response.status_code}")
        try:
            # Using response.text to print the content of the response
            print("[DEBUG] Response content:", response.text)
        except Exception as e:
            print("[ERROR] Could not decode response content:", e)


    # @task
    # def query_already_sold_orders(self):
    #     random_order = random.choice(self.getAllOrders())
    #     travel_date = random_order['travelDate']
    #     train_number = random_order['trainNumber']
    #     response = self.client.post(self.get_addr('order-service', "/api/v1/orderservice/order/query_already_sold_orders"),
    #                              json = {
    #                                  "travelDate": travel_date,
    #                                  "trainNumber": train_number
    #                              }, headers=self.auth_headers())

    @task
    def get_left_ticket_of_interval(self):
        travel_date = get_random_time(100)
        trip = random.choice(self.getAllTrips())
        train_number = trip['tripId']['type'] + trip['tripId']['number']
        route = self.get_route_from_trip(trip)
        ids = random.sample(range(0, len(route['stations'])), 2)
        ids.sort()
        start_station = route['stations'][ids[0]]
        dest_station = route['stations'][ids[1]]
        response = self.client.post(self.get_addr('seat-service', "/api/v1/seatservice/seats/left_tickets"),
                                 json = {
                                     "travelDate": travel_date,
                                     "trainNumber": train_number,
                                     "startStation": start_station,
                                     "destStation": dest_station,
                                     "seatType": random.choice([1, 2, 3, 4, 5, 6, 7, 8])
                                 }, headers=self.auth_headers())

    @task
    def place_random_order(self):
        # Get all routes
        routes = self.getAllRoutes()
        if not routes:
            print("[DEBUG] No routes available for placing an order. Aborting task.")
            return
        # Pick one random route and extract the 'stations' list
        route = random.choice(routes)['stations']
        if not route or len(route) < 2:
            print("[DEBUG] Not enough stations in selected route. Aborting task.")
            return
        route_ids = random.sample(range(0, len(route)), 2)
        route_ids.sort()
        start, end = route[route_ids[0]], route[route_ids[1]]
        trip_date_time = get_random_time(100)
        print(f"[DEBUG] Placing order: start station: {start}, end station: {end}, date: {trip_date_time}")

        # Get a trip between the selected stations
        trip = self.get_a_trip_between_stations(start, end, trip_date_time)
        if trip is None:
            print("[DEBUG] No trip found between stations; order aborted.")
            return
        tripId = trip.get('tripId')
        if not tripId:
            print("[DEBUG] Trip does not contain a tripId; order aborted.")
            return

        # Get a contact id from contacts
        contacts = self.getAllContacts()
        if not contacts:
            print("[DEBUG] No contacts available; cannot place order.")
            return
        contact_id = random.choice(contacts).get('id')
        if not contact_id:
            print("[DEBUG] Selected contact does not contain an id; aborting order.")
            return

        # Get food for the trip
        food_list = self.get_food_for_trip(trip_date_time, trip.get('startingStation'), trip.get('terminalStation'), tripId)
        print(f"[DEBUG] Food list returned: {food_list}")
        food = None
        if food_list is None:
            print("[DEBUG] food_list is None; no food will be selected.")
        else:
            # First, try to get food from 'trainFoodList'
            if ('trainFoodList' in food_list and 
                isinstance(food_list['trainFoodList'], list) and 
                len(food_list['trainFoodList']) > 0 and 
                isinstance(food_list['trainFoodList'][0], dict) and 
                'foodList' in food_list['trainFoodList'][0] and 
                food_list['trainFoodList'][0]['foodList']):
                try:
                    food = random.choice(food_list['trainFoodList'][0]['foodList'])
                    print(f"[DEBUG] Selected food from trainFoodList: {food}")
                except Exception as e:
                    print(f"[ERROR] Exception selecting food from trainFoodList: {e}")
            # If no food from trainFoodList, try foodStoreListMap
            if food is None and 'foodStoreListMap' in food_list and food_list['foodStoreListMap']:
                try:
                    fsmap = food_list['foodStoreListMap']
                    # Ensure fsmap is a dict and has values
                    if isinstance(fsmap, dict) and fsmap.values():
                        # Pick a random value from the map, which should be a list of stores
                        store_list = list(fsmap.values())
                        # Check if the selected store list is a list with a dict having 'foodList'
                        if store_list and isinstance(store_list[0], list) and store_list[0]:
                            candidate = random.choice(store_list[0])
                            if 'foodList' in candidate and candidate['foodList']:
                                food = random.choice(candidate['foodList'])
                                print(f"[DEBUG] Selected food from foodStoreListMap: {food}")
                except Exception as e:
                    print(f"[ERROR] Exception selecting food from foodStoreListMap: {e}")
        
        if food is None:
            print("[DEBUG] No food selected; aborting order placement.")
            return

        order_request_data = {
            "accountId": self.userId,
            "contactsId": contact_id,
            "tripId": tripId,
            "seatType": random.choice([1, 2, 3, 4, 5, 6, 7, 8]),
            "date": trip_date_time,
            "from": trip.get('startingStation'),
            "to": trip.get('terminalStation'),
            "assurance": "",
            "foodType": "",
            "stationName": trip.get('startingStation'),
            "storeName": "",
            "foodName": food.get('foodName') if isinstance(food, dict) else "",
            "foodPrice": food.get('price') if isinstance(food, dict) else "",
            "handleDate": "",
            "consigneeName": "",
            "consigneePhone": "",
            "consigneeWeight": "",
            "isWithin": "",
        }

        url = self.get_addr('preserve-service', "/api/v1/preserveservice/preserve")
        print(f"[DEBUG] Placing order with data: {order_request_data} to URL: {url}")
        response = self.client.post(url, json=order_request_data, headers=self.auth_headers())
        try:
            resp_content = response._content.decode('utf-8')
        except Exception as e:
            resp_content = str(e)
        print(f"[DEBUG] Order response - Status: {response.status_code}, Content: {resp_content}")

class AdminUser(HttpUser):
    weight = 1
    host = "http://10.102.65.26:32677"
    # weight = 100
    wait_time = between(1, 2.5)

    ip_map, port_map = get_ip_map()

    def get_addr(self, service, path):
        return 'http://' + NormalUser.ip_map[service] + ':' + NormalUser.port_map[service] + path

    def auth_headers(self):
        return {'Authorization': 'Bearer ' + self.token}

    def on_start(self):
        username = 'fdse_microservice'
        password = '111111'
        self.login(username, password)

    def login(self, username, password):
        url = self.get_addr('ui-dashboard', "/api/v1/users/login")
        payload = {'username': username, 'password': password, 'verificationCode': '1234'}
        print(f"[DEBUG] Logging in with URL: {url} and payload: {payload}")
        response = self.client.post(url, json=payload)
        print(f"[DEBUG] Login response status: {response.status_code}")
        try:
            resp_json = json.loads(response._content.decode('utf-8'))
            print(f"[DEBUG] Login response JSON: {resp_json}")
        except Exception as e:
            print(f"[ERROR] Failed to parse JSON response: {e}")
            resp_json = {}
        data = resp_json.get('data')
        if not data:
            print(f"[ERROR] Login failed, no data in response. Full response: {response._content.decode('utf-8')}")
            # Optionally, you can set a default token or exit
            return
        self.token = data.get('token')
        self.userId = data.get('userId')
        print(f"[DEBUG] Login successful. Token: {self.token}, UserID: {self.userId}")


    def getAllTrips(self):
        response = self.client.get(self.get_addr('travel-service', "/api/v1/travelservice/trips"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def getAllStations(self):
        response = self.client.get(self.get_addr('station-service', "/api/v1/stationservice/stations"), headers=self.auth_headers())
        return json.loads(response._content)['data']

    def get_route_from_trip(self, trip):
       response = self.client.get(self.get_addr('route-service', "/api/v1/routeservice/routes/" + trip['routeId']),
                               headers=self.auth_headers())
       return json.loads(response._content)['data']

    def get_random_routes_and_trips(self, stations, num):
        routes = []
        trips = []
        for i in range(num):
            route_ids = random.sample(range(0, len(stations)), random.randint(2, len(stations)))
            station_list = [stations[i]['id'] for i in route_ids]
            distance_list = [random.randint(10, 100) for i in route_ids]
            distance_list.sort()
            route_info = {
                "id": str(uuid.uuid4()),
                "startStation": stations[route_ids[0]]['name'],
                "endStation": stations[route_ids[-1]]['name'],
                "stationList": ','.join(station_list),
                "distanceList": ','.join([str(i) for i in distance_list])
            }
            routes.append(route_info)
            start_time = get_random_time(100)
            end_time = start_time + random.randint(1, 6) * 60 * 60 * 1000
            trips.append({
                "tripId": random.choice(['G', 'D']) + str(random.randint(1000, 9999)),
                "trainTypeId": "GaoTieOne",
                "routeId": route_info['id'],
                "startingStationId": stations[route_ids[0]]['id'],
                "stationsId": stations[route_ids[1]]['id'],
                "terminalStationId": stations[route_ids[-1]]['id'],
                "startingTime": start_time,
                "endTime": end_time
            })
        return routes, trips


    # Modify stations and routes
    @task
    def delete_trip_and_route(self):
        trip = random.choice(self.getAllTrips())
        tripId = trip['tripId']['type'] + trip['tripId']['number']
        routeId = trip['tripId']['type'] + trip['tripId']['number']

        response = self.client.delete(self.get_addr('travel-service', "/api/v1/travelservice/trips" + tripId),
                                      headers=self.auth_headers())
        response = self.client.delete(self.get_addr('route-service', "/api/v1/routeservice/routes" + routeId),
                                      headers=self.auth_headers())

    @task
    def delete_station(self):
        station = random.choice(self.getAllStations())
        for trip in self.getAllTrips():
            tripId = trip['tripId']['type'] + trip['tripId']['number']
            routeId = trip['tripId']['type'] + trip['tripId']['number']
            route = self.get_route_from_trip(trip)
            stations = route['stations']
            without_station = stations.copy()
            if station in without_station:
                without_station.remove(station)
            if len(without_station) == len(stations):
                continue
            elif stations[0] == station or stations[-1] == station:
                response = self.client.delete(self.get_addr('travel-service', "/api/v1/travelservice/trips" + tripId),
                                              headers=self.auth_headers())
                response = self.client.delete(self.get_addr('route-service', "/api/v1/routeservice/routes" + routeId),
                                              headers=self.auth_headers())
            else:
                route_info = {
                    "id": route['id'],
                    "startStation": stations[0],
                    "endStation": stations[-1],
                    "stationList": ','.join(stations),
                    "distanceList": ','.join(route['distances']),
                }
                response = self.client.post(self.get_addr('route-service', "/api/v1/routeservice/routes"),
                                            json = route_info,
                                            headers=self.auth_headers())

            response = self.client.delete(self.get_addr('station-service', "/api/v1/stationservice/stations"),
                                          json = station, headers=self.auth_headers())

    @task
    def add_random_station(self):
        id = str(uuid.uuid4())
        station = {
            "id": id,
            "name": "name" + id,
            "stayTime": random.randint(0, 20)
        }
        self.client.post(self.get_addr('station-service', "/api/v1/stationservice/stations"),
                      json = station, headers=self.auth_headers())

    @task
    def add_random_route(self):
        stations = self.getAllStations()

        routes, trips = self.get_random_routes_and_trips(stations, 1)
        for route in routes:
            response = self.client.post(self.get_addr('route-service', "/api/v1/routeservice/routes"),
                                     json = route, headers=self.auth_headers())

        for trip in trips:
            response = self.client.post(self.get_addr('travel-service', "/api/v1/travelservice/trips"),
                                     json = trip, headers=self.auth_headers())



    def create_random_food(self):
        return {
            "foodName": "food_name" + str(random.randint(0, 10000000)),
            "price": random.randint(10, 100) * 1.0
        }


    def getAllFoodStores(self):
        response = self.client.get(self.get_addr('food-map-service', "/api/v1/foodmapservice/foodstores"),
                                   headers=self.auth_headers())
        return json.loads(response._content)['data']

    def getAllTrainFoods(self):
        response = self.client.get(self.get_addr('food-map-service', "/api/v1/foodmapservice/trainfoods"),
                                   headers=self.auth_headers())
        return json.loads(response._content)['data']

    # Modify food
    @task
    def modify_foodstore(self):
        foodstore = random.choice(self.getAllFoodStores())
        if random.choice([0, 1]) == 0:
            foodstore['foodList'].append(self.create_random_food())
        else:
            foodstore['foodList'].pop(random.randint(0, len(foodstore['foodList']) - 1))
        response = self.client.delete(self.get_addr('food-map-service',
                                                 "/api/v1/foodmapservice/foodstores/delete/" + foodstore['id']),
                                   headers=self.auth_headers())
        response = self.client.post(self.get_addr('food-map-service', "/api/v1/foodmapservice/foodstores/create"),
                                 json = foodstore, headers=self.auth_headers())

    @task
    def modify_trainfood(self):
        trainfood = random.choice(self.getAllTrainFoods())
        if random.choice([0, 1]) == 0:
            trainfood['foodList'].append(self.create_random_food())
        else:
            trainfood['foodList'].pop(random.randint(0, len(trainfood['foodList']) - 1))
        response = self.client.delete(self.get_addr('food-map-service',
                                                 "/api/v1/foodmapservice/trainfoods/delete/" + trainfood['id']),
                                   headers=self.auth_headers())
        response = self.client.post(self.get_addr('food-map-service', "/api/v1/foodmapservice/trainfoods/create"),
                                 json = trainfood, headers=self.auth_headers())
