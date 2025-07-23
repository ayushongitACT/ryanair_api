import json
from cookies import get_cookies as cookie
from cookies import get_headers as header
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def get_return_price_options(outflightkey,outfarekey,infightkey,infarekey,adult,teen,child,infant,locale,headers,cookies):
    
   
    try:
        response = requests.get(
            f'https://www.ryanair.com/api/booking/v5/{locale}/FareOptions?OutboundFlightKey={outflightkey}&OutboundFareKey={outfarekey}&AdultsCount={adult}&ChildrenCount={child}&InfantCount={infant}&TeensCount={teen}&InboundFlightKey={infightkey}&InboundFareKey={infarekey}',
            cookies=cookies,
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            fare_types = {
                "REGU": "REGULAR",
                "SURE": "PLUS",
                "PLUS": "FLEXI PLUS",
                "FAMI": "FAMILY PLUS"
            }
            
            fare_prices = []
            for item in data:
                price_info = {
                    "code": fare_types[item['code']],
                    "price": item['perPerson']['total'] if item['code'] == 'FAMI' else item['total']
                }
                fare_prices.append(price_info)
            
            # Process unique codes and average prices
            unique_fares = {}
            for fare in fare_prices:
                code = fare['code']
                if code in unique_fares:
                    unique_fares[code].append(fare['price'])
                else:
                    unique_fares[code] = [fare['price']]
            
            # Calculate averages and round to 2 decimal places
            final_prices = []
            for code, prices in unique_fares.items():
                avg_price = round(sum(prices) / 2, 2)  # Divide by 2 and round to 2 decimals
                final_prices.append({
                    "code": code,
                    "price": avg_price
                })
            basic_fare_features = ['1 small bag']
            regular_fare_features = ['1 small bag','Reserved seat','Priority boarding','10kg overhead locker bag']
            plus_fare_features = ['1 small bag','Reserved seat','20kg check-in bag','Free check-in at the airport']
            flexi_plus_fare_features = ['1 small bag','Reserved seat','Priority boarding','10kg overhead locker bag','Free check-in at the airport','Speed through security','Change flights with no fees','Move to an earlier flight']
            family_fare_features = ['1 small bag','Free seats for kids under 12','10kg check-in bag for all','20kg check-in bag']
            for fare in fare_prices:
                if fare['code'] == 'BASIC':
                    fare['features'] = basic_fare_features
                elif fare['code'] == 'REGULAR':
                    fare['features'] = regular_fare_features
                elif fare['code'] == 'PLUS':
                    fare['features'] = plus_fare_features
                elif fare['code'] == 'FLEXI PLUS':
                    fare['features'] = flexi_plus_fare_features
                elif fare['code'] == 'FAMILY PLUS':
                    fare['features'] = family_fare_features
            return final_prices
        else:
            print(f"Price request failed with status code {response.status_code}")
            return None
    except Exception as e:
        # print(f"An error occurred: {e}")
        return None
        
def create_combinations_without_addons(data, passenger_count):
    try:
     
        combinations = []
        url = data[0]['url']
        outbound_flights = data[0]['flights']
        return_flights = data[1]['flights']
        outbound_route = data[0]['route']
        return_route = data[1]['route']
        for outbound in outbound_flights:
            outbound_total = sum(fare['base_amount']*fare['passenger_count'] for fare in outbound['fares'])
            
            for return_flight in return_flights:
                return_total = sum(fare['base_amount']*fare['passenger_count'] for fare in return_flight['fares'])
                
                basic_price = outbound_total + return_total 
                
                combination = {
                    
                    'outbound': {
                        'date': outbound['date'],
                        'flight_key': outbound['flight_key'],
                        'fare_key': outbound['fare_key'],
                        'flight_number': outbound['flight_number'],
                        'departure_time': outbound['departure_time'],
                        'arrival_time': outbound['arrival_time'],
                        'duration': outbound['duration'],
                        'total_fare': outbound_total,
                        'mandatory_amount': outbound['mandatory_amount'],
                        'infant_amount': outbound['infant_amount'],
                        
                    },
                    'return': {
                        'date': return_flight['date'],
                        'flight_key': return_flight['flight_key'],
                        'fare_key': return_flight['fare_key'],
                        'flight_number': return_flight['flight_number'],
                        'departure_time': return_flight['departure_time'],
                        'arrival_time': return_flight['arrival_time'],
                        'duration': return_flight['duration'],
                        'total_fare': return_total,
                        'mandatory_amount': return_flight['mandatory_amount'],
                        'infant_amount': return_flight['infant_amount'],
                    },
                    'basic_price_per_person': basic_price/passenger_count,
                    'total_basic_price': basic_price+outbound['mandatory_amount']+return_flight['mandatory_amount']+outbound['infant_amount']+return_flight['infant_amount'],
                }
                combinations.append(combination)
     
        return {
            'url': url,
            'currency':data[0]['currency'], #currency dat
            'outbound_route': outbound_route,
            'return_route': return_route,
            'combinations': combinations
        }

    except Exception as e:
        # print(f"An error occurred in combinations: {e}")
        return None

def fetch_addons_for_combination(combination, passenger_count,adult,teen,child,infant,locale,headers,cookies):

    add_ons = get_return_price_options(
        combination['outbound']['flight_key'],
        combination['outbound']['fare_key'],
        combination['return']['flight_key'],
        combination['return']['fare_key'],
        adult,
        teen,
        child,
        infant,
        locale,
        headers,
        cookies,
    )

    # Add BASIC option using values from combination
    basic_option = {
        'code': 'BASIC',
        'price': 0,
        'per_passenger_price': round(combination['basic_price_per_person'], 2),
        'total_price': round(combination['total_basic_price'], 2),
        'features':[
                    "1 small bag",
                    {
                        "seat_pre_reservation": "fee",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": []
                    }
                ]
    }

    # Start building price_options with BASIC
    price_options = [basic_option]

    if add_ons:
        for addon in add_ons:
            total_with_addon = (
                combination['outbound']['total_fare'] +
                combination['return']['total_fare'] +
                ((addon['price'] * passenger_count )* 2)
            )
            addon['per_passenger_price'] = round(total_with_addon / passenger_count, 2)
            if addon['code'] == 'FAMILY PLUS':
                addon['total_price'] = round((
                    total_with_addon +
                    combination['outbound']['mandatory_amount'] +
                    combination['return']['mandatory_amount'] +
                    combination['outbound']['infant_amount'] +
                    combination['return']['infant_amount']
                ),2)
            else:
                addon['total_price'] = round(total_with_addon+combination['outbound']['infant_amount']+combination['return']['infant_amount'],2)

            price_options.append(addon)
        regular_fare =[
                    "1 small bag",
                    "Reserved seat",
                    "Priority boarding",
                    "10kg overhead locker bag",
                    {
                        "seat_pre_reservation": "included",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": [
                            {
                                "type": "cabin",
                                "size": {
                                    "dimensions": "55 x 40 x 20 cm",
                                    "weight": "10",
                                    "unit": "kg"
                                }
                            }
                        ]
                    }
                ]
            

        plus_fare = [
                "1 small bag",
                "Reserved seat",
                "20kg check-in bag",
                "Free check-in at the airport",
                {
                    "seat_pre_reservation": "included",
                    "advance_change": "unavailable",
                    "cancellation_policy": "unavailable"
                },
                {
                    "baggage": [
                        {
                            "type": "check-in",
                            "size": {
                                "dimensions": "N/A",
                                "weight": "20",
                                "unit": "kg"
                            }
                        }
                    ]
                }
            ]
        

        flexi_plus_fare = [
                "1 small bag",
                "Reserved seat",
                "Priority boarding",
                "10kg overhead locker bag",
                "Free check-in at the airport",
                "Speed through security",
                "Change flights with no fees",
                "Move to an earlier flight",
                {
                    "seat_pre_reservation": "included",
                    "advance_change": "unavailable",
                    "cancellation_policy": "unavailable"
                },
                {
                    "baggage": [
                        {
                            "type": "cabin",
                            "size": {
                                "dimensions": "55 x 40 x 20 cm",
                                "weight": "10",
                                "unit": "kg"
                            }
                        }
                    ]
                }
            ]
        

        family_fare = [
                "1 small bag",
                "Free seats for kids under 12",
                "Reserved seat",
                "10kg check-in bag for all",
                "20kg check-in bag",
                {
                    "seat_pre_reservation": "included",
                    "advance_change": "unavailable",
                    "cancellation_policy": "unavailable"
                },
                {
                    "baggage": [
                        {
                            "type": "check-in",
                            "size": {
                                "dimensions": "N/A",
                                "weight": "10",
                                "unit": "kg"
                            }
                        },
                        {
                            "type": "check-in",
                            "size": {
                                "dimensions": "N/A",
                                "weight": "20",
                                "unit": "kg"
                            }
                        }
                    ]
                }
            ]
        for fare in price_options:
            if fare['code'] == 'REGULAR':
                fare['features'] = regular_fare
            elif fare['code'] == 'PLUS':
                fare['features'] = plus_fare
            elif fare['code'] == 'FLEXI PLUS':
                fare['features'] = flexi_plus_fare
            elif fare['code'] == 'FAMILY PLUS':
                fare['features'] = family_fare
    # Attach price options and remove basic pricing fields
        combination['price_options'] = price_options
        combination.pop('basic_price_per_person', None)
        combination.pop('total_basic_price', None)

        return combination
    else:
        # print("No add-ons found.")
        return None



def create_flight_combinations(data,passenger_count,adult,teen,child,infant,locale):
    
    # First create all combinations without add-ons
    combinations = create_combinations_without_addons(data, passenger_count)
    if combinations:
        
        cookies = cookie()
        headers = header()
        # Then fetch add-ons using threading
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_combination = {
                executor.submit(fetch_addons_for_combination, combination, passenger_count,adult,teen,child,infant,locale,headers,cookies): combination 
                for combination in combinations['combinations']
            }
            
            completed_combinations = []
            for future in as_completed(future_to_combination):
                try:
                    completed_combination = future.result()
                    if not completed_combination:
                        # print("No add-ons found for this combination.")
                        return None
                    completed_combinations.append(completed_combination)
                except Exception as e:
                    # print(f"Error fetching add-ons: {str(e)}")
                    return None
        result ={
            'url': combinations['url'],
            'currency': combinations['currency'], #currency data
            'route':{
            'outbound_route': combinations['outbound_route'],
            'return_route': combinations['return_route'],
            },
            'flights' : completed_combinations
            }
        
        return result
    else:
        # print("No combinations found.")
        return None
def get_oneway_price_options(OutboundFlightKey,OutboundFareKey,adults,childern,infant,teens,t,mandatory_amount,infant_amount,locale,headers,cookies):
    try:
        response = requests.get(
            f'https://www.ryanair.com/api/booking/v5/{locale}/FareOptions?OutboundFlightKey={OutboundFlightKey}&OutboundFareKey={OutboundFareKey}&AdultsCount={str(adults)}&ChildrenCount={str(childern)}&InfantCount={str(infant)}&TeensCount={str(teens)}',
            cookies=cookies,
            headers=headers,
            # params=params,
        )
        if response.status_code == 200:
            data = response.json()
            fare_types = {
                "REGU": "REGULAR",
                "SURE": "PLUS",
                "PLUS": "FLEXI PLUS",
                "FAMI": "FAMILY PLUS"
            }

            total = sum([int(adults), int(childern), int(teens)])
            fare_prices = []
            fare_prices.append({
                    "code" : "BASIC",
                    "per_passenger_price": round(t/total,2),
                    "total_price": round((t+mandatory_amount+infant_amount),2),
                })
            
            # print(total)
            # print(t)
            for item in data:
                per_passanger_price = (((t)+(float(item['perPerson']['total'])*total))/total) if item['code'] == 'FAMI' else (((t)+(item['total']*total))/total)
                # print(item['perPerson']['total'] if item['code'] == 'FAMI' else item['total'])
                # print(((t*total)+(item['perPerson']['total']*total)))
                if fare_types[item['code']] == "FAMILY PLUS":
                    total_price = (per_passanger_price*total)+mandatory_amount+infant_amount
                else:
                    total_price = (per_passanger_price*total)+infant_amount
                price_info = {
                    "code": fare_types[item['code']],
                    "per_passenger_price": round(per_passanger_price,2),
                    "price" : item['perPerson']['total'] if item['code'] == 'FAMI' else item['total'],
                    "total_price":round(total_price,2)
                }
                # print(price_info)
            
                fare_prices.append(price_info)
            
            basic_fare = [
                    "1 small bag",
                    {
                        "seat_pre_reservation": "fee",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": []
                    }
                ]
            

            regular_fare =[
                    "1 small bag",
                    "Reserved seat",
                    "Priority boarding",
                    "10kg overhead locker bag",
                    {
                        "seat_pre_reservation": "included",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": [
                            {
                                "type": "cabin",
                                "size": {
                                    "dimensions": "55 x 40 x 20 cm",
                                    "weight": "10",
                                    "unit": "kg"
                                }
                            }
                        ]
                    }
                ]
            

            plus_fare = [
                    "1 small bag",
                    "Reserved seat",
                    "20kg check-in bag",
                    "Free check-in at the airport",
                    {
                        "seat_pre_reservation": "included",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": [
                            {
                                "type": "check-in",
                                "size": {
                                    "dimensions": "N/A",
                                    "weight": "20",
                                    "unit": "kg"
                                }
                            }
                        ]
                    }
                ]
            

            flexi_plus_fare = [
                    "1 small bag",
                    "Reserved seat",
                    "Priority boarding",
                    "10kg overhead locker bag",
                    "Free check-in at the airport",
                    "Speed through security",
                    "Change flights with no fees",
                    "Move to an earlier flight",
                    {
                        "seat_pre_reservation": "included",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": [
                            {
                                "type": "cabin",
                                "size": {
                                    "dimensions": "55 x 40 x 20 cm",
                                    "weight": "10",
                                    "unit": "kg"
                                }
                            }
                        ]
                    }
                ]
            

            family_fare = [
                    "1 small bag",
                    "Free seats for kids under 12",
                    "Reserved seat",
                    "10kg check-in bag for all",
                    "20kg check-in bag",
                    {
                        "seat_pre_reservation": "included",
                        "advance_change": "unavailable",
                        "cancellation_policy": "unavailable"
                    },
                    {
                        "baggage": [
                            {
                                "type": "check-in",
                                "size": {
                                    "dimensions": "N/A",
                                    "weight": "10",
                                    "unit": "kg"
                                }
                            },
                            {
                                "type": "check-in",
                                "size": {
                                    "dimensions": "N/A",
                                    "weight": "20",
                                    "unit": "kg"
                                }
                            }
                        ]
                    }
                ]
            

            for fare in fare_prices:
                if fare['code'] == 'BASIC':
                    fare['features'] = basic_fare
                elif fare['code'] == 'REGULAR':
                    fare['features'] = regular_fare
                elif fare['code'] == 'PLUS':
                    fare['features'] = plus_fare
                elif fare['code'] == 'FLEXI PLUS':
                    fare['features'] = flexi_plus_fare
                elif fare['code'] == 'FAMILY PLUS':
                    fare['features'] = family_fare
            return fare_prices
        else:
            # print(f"Error fetching one way price options: {response.status_code}")
            return None
    except Exception as e:
        # print(f"Error fetching one way price options: {str(e)}")
        return None
def get_oneway_flight(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,roundtrip_check):
    cookies = cookie()

    headers = header()
    params = {
        'ADT': adult,
        'TEEN': teen,
        'CHD': child,
        'INF': infant,
        'Origin': origin,
        'Destination': destinaiton,
        'promoCode': '',
        'IncludeConnectingFlights': 'false',
        'DateOut': dateout,
        'DateIn': datein,
        'FlexDaysBeforeOut': '2',
        'FlexDaysOut': '2',
        'FlexDaysBeforeIn': '2',
        'FlexDaysIn': '2',
        'RoundTrip': roundtrip_check,
        'IncludePrimeFares': 'false',
        'ToUs': 'AGREED',
    }

    try:
        
        response = requests.get(
            f'https://www.ryanair.com/api/booking/v4/{locale}/availability',
            params=params,
            cookies=cookies,
            headers=headers,
        )

        if response.status_code not in [200, 404]:
            return {"status":500,"Error":"Internal Server Error"}
        if response.status_code == 404:
            return {"status":response.status_code, "Error":"StationNotFound"}

        country = locale.split('-')[-1]
        language = locale.split('-')[0]
        data = response.json()

        flight_results = []
        trips = data.get('trips', [])
        flights_count = 0

        futures = []
        final_flights = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            for trip in trips:
                route_info = {
                    'url': f'https://www.ryanair.com/{country}/{language}/trip/flights/select?adults={adult}&teens={teen}&children={child}&infants={infant}&dateOut={dateout}&dateIn={datein}&isConnectedFlight=false&discount=0&isReturn=false&promoCode=&originIata={origin}&destinationIata={destinaiton}&tpAdults={adult}&tpTeens={teen}&tpChildren={child}&tpInfants={infant}&tpStartDate={dateout}&tpEndDate={datein}&tpDiscount=0&tpPromoCode=&tpOriginIata={origin}&tpDestinationIata={destinaiton}',
                    'currency': data.get('currency', ''),
                    'route': {
                        'outbound_route': {
                            'origin': {
                                'name': trip.get('originName'),
                                'code': trip.get('origin')
                            },
                            'destination': {
                                'name': trip.get('destinationName'),
                                'code': trip.get('destination')
                            }
                        },
                        'return_route': {}
                    },
                    'flights': []
                }

                arrival_filtered_dates = [
                    date for date in trip.get('dates', [])
                    if date.get('dateOut') == f"{params['DateOut']}T00:00:00.000"
                ]

                for date in arrival_filtered_dates:
                    date_out = date.get('dateOut')
                    flights = date.get('flights', [])

                    for flight in flights:
                        outbound_info = {
                            'date': date_out,
                            'flight_number': flight.get('flightNumber'),
                            'flight_key': flight.get('flightKey'),
                        }

                        segments = flight.get('segments', [])
                        if segments:
                            segment = segments[0]
                            times = segment.get('time', [])
                            if len(times) >= 2:
                                outbound_info['departure_time'] = times[0]
                                outbound_info['arrival_time'] = times[1]
                            outbound_info['duration'] = segment.get('duration')

                        regular_fare = flight.get('regularFare', {})
                        total_fare = 0
                        mandatory_total = 0
                        infant_fare = 0
                        fare_key = ""

                        if regular_fare:
                            fare_key = regular_fare.get('fareKey')
                            if fare_key:
                                flights_count += 1
                                outbound_info['fare_key'] = fare_key

                                for fare in regular_fare.get('fares', []):
                                    mandatory_seat_fee = fare.get("mandatorySeatFee", {})
                                    infant_fee = fare.get("infantFee", {})

                                    base_amount = fare.get('amount')
                                    count = fare.get('count', 0)
                                    mandatory_amount = mandatory_seat_fee.get("totalWithoutDiscount", 0)
                                    infant_amount = infant_fee.get("totalWithoutDiscount", 0)

                                    total_fare += base_amount * count
                                    mandatory_total += mandatory_amount
                                    infant_fare += infant_amount

                                # Submit to thread pool
                                futures.append(
                                    executor.submit(
                                        get_oneway_price_options,
                                        outbound_info['flight_key'],
                                        fare_key,
                                        adult,
                                        child,
                                        infant,
                                        teen,
                                        total_fare,
                                        mandatory_total,
                                        infant_fare,
                                        locale,
                                        headers,
                                        cookies
                                    )
                                )

                                # Store meta to match later
                                final_flights.append((route_info, outbound_info))

                if route_info['flights']:
                    flight_results.append(route_info)

            # --- Collect threaded results ---
            for i, future in enumerate(as_completed(futures)):
                price_option = future.result()
                route_info, outbound_info = final_flights[i]

                if price_option:
                    route_info['flights'].append({
                        'outbound': outbound_info,
                        'return': {},
                        'price_options': price_option
                    })

                    if route_info not in flight_results:
                        flight_results.append(route_info)
                else:
                    continue

        if flights_count == 0:
            return {"status":404,"Error":"flights are not available"}

        return flight_results

    except Exception as e:
        return {"status":500,"Error":"Internal Server Error"}


def get_return_flight(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,trip):
    cookies = cookie()
    headers = header()
    params = {
    'ADT': adult,
    'TEEN': teen,
    'CHD': child,
    'INF': infant,
    'Origin': origin,
    'Destination': destinaiton,
    'promoCode': '',
    'IncludeConnectingFlights': 'false',
    'DateOut': dateout,
    'DateIn': datein,
    'FlexDaysBeforeOut': '2',
    'FlexDaysOut': '2',
    'FlexDaysBeforeIn': '2',
    'FlexDaysIn': '2',
    'RoundTrip': trip,
    'IncludePrimeFares': 'false',
    'ToUs': 'AGREED',
    }
    try:
        response = requests.get(
            f'https://www.ryanair.com/api/booking/v4/{locale}/availability',
            params=params,
            cookies=cookies,
            headers=headers,
        )
        if response.status_code not in [200, 404]:
            return {"status":500,"Error":"Internal Server Error"},0
        if response.status_code == 404:
            return {"status":response.status_code,"Error":"StationNotFound"},0
        country = locale.split('-')[-1]
        language = locale.split('-')[0]
        passenger_count = int(adult) + int(teen) + int(child) 
        data = response.json()
        currency = data.get('currency', '')
        trips = data.get('trips', [])
        flight_results = []

        search_url = (
            f'https://www.ryanair.com/{country}/{language}/trip/flights/select?adults={adult}&teens={teen}&children={child}'
            f'&infants={infant}&dateOut={dateout}&dateIn={datein}&isConnectedFlight=false&discount=0&isReturn=false'
            f'&promoCode=&originIata={origin}&destinationIata={destinaiton}&tpAdults={adult}&tpTeens={teen}'
            f'&tpChildren={child}&tpInfants={infant}&tpStartDate={dateout}&tpEndDate={datein}&tpDiscount=0'
            f'&tpPromoCode=&tpOriginIata={origin}&tpDestinationIata={destinaiton}'
        )

        count = 0
        outbound_flights_count = 0  # Track available flights
        retrun_flight_count = 0
        for trip in trips:
            count += 1
            route_info = {
                'url': search_url,
                'currency': currency,
                'route': {
                    'origin': {
                        'name': trip.get('originName'),
                        'code': trip.get('origin')
                    },
                    'destination': {
                        'name': trip.get('destinationName'),
                        'code': trip.get('destination')
                    }
                },
                'flights': []
            }

            if count == 1:
                expected_date = f"{params['DateOut']}T00:00:00.000"
            elif count == 2:
                if not params.get('DateIn'):
                    continue
                expected_date = f"{params['DateIn']}T00:00:00.000"
            else:
                continue

            for date in trip.get('dates', []):
                if date.get('dateOut') == expected_date:
                    date_out = date.get('dateOut')
                    for flight in date.get('flights', []):
                        flight_info = {
                            'date': date_out,
                            'flight_number': flight.get('flightNumber'),
                            'flight_key': flight.get('flightKey'),
                            'fares': []
                        }

                        # Add segments info as before
                        segments = flight.get('segments', [])
                        if segments:
                            segment = segments[0]
                            times = segment.get('time', [])
                            if len(times) >= 2:
                                flight_info['departure_time'] = times[0]
                                flight_info['arrival_time'] = times[1]
                            flight_info['duration'] = segment.get('duration')
                        
                        regular_fare = flight.get('regularFare', {})
                        if regular_fare:
                            fare_key = regular_fare.get('fareKey')
                            if fare_key:  # Only process flights with valid fare keys
                                if count == 1:
                                    outbound_flights_count += 1
                                elif count == 2:
                                    retrun_flight_count += 1
                                flight_info['fare_key'] = fare_key
                                mandatory_amount = 0
                                infant_amount = 0
                                for fare in regular_fare.get('fares', []):
                                    seat_fee = fare.get("mandatorySeatFee", {})
                                    infant_fee = fare.get("infantFee", {})
                                    fare_info = {
                                        'type': fare.get('type'),
                                        'base_amount': fare.get('amount'),
                                        'published_fare': fare.get('publishedFare'),
                                        'passenger_count': fare.get('count'),
                                        'discount_amount': fare.get('discountAmount'),
                                        'mandatory_amount': seat_fee.get("totalWithoutDiscount", 0),
                                        'infant_amount': infant_fee.get("totalWithoutDiscount", 0),
                                    }
                                    mandatory_amount += fare_info['mandatory_amount']
                                    infant_amount += fare_info['infant_amount']
                                    flight_info['fares'].append(fare_info)
                                flight_info['mandatory_amount'] = mandatory_amount
                                flight_info['infant_amount'] = infant_amount
                                route_info['flights'].append(flight_info)
            
            if route_info['flights']:  # Only append if there are available flights
                flight_results.append(route_info)
            
        if outbound_flights_count == 0 or retrun_flight_count == 0:
                return {"status":404,"Error":"flights are not available"},0

        return flight_results,passenger_count
    except Exception as e:
        return {"status":500,"Error":"Internal Server Error"},0


def get_addtional_luggage_oneway(flight,flight_key,fare_key,locale,adult,teen,child,infant,headers,cookies):

    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
           
            sess = requests.Session()
            json_data = {
            'query': 'mutation CreateBasket {\n  createBasket {\n    ...BasketCommon\n    gettingAround {\n      ...GettingAroundPillar\n    }\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\nfragment VariantCar on VariantUnionType {\n  ... on Car {\n    rentPrice\n    carName\n    refId\n    engineLoadId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    extras {\n      totalPrice\n      includedInRate\n      code\n      price\n      selected\n      type\n    }\n    residence\n    age\n  }\n}\n\nfragment VariantCarRental on VariantUnionType {\n  ... on CarRental {\n    rentPrice\n    carName\n    clientId\n    refId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    insuranceQuoteReference\n    extras {\n      code\n      includedInRate\n      payNow\n      price\n      selected\n      totalPrice\n      type\n    }\n    residence\n    age\n    language\n    searchId\n    supplier\n  }\n}\n\nfragment GettingAroundPillar on GettingAroundType {\n  price {\n    amount\n    discount\n    amountWithTaxes\n    total\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  taxes {\n    amount\n  }\n  components {\n    ...ComponentCommon\n    payLater {\n      amountWithTaxes\n      total\n    }\n    variant {\n      ...VariantCar\n      ...VariantCarRental\n      ...VariantGroundTransfer\n    }\n  }\n}\n\n',
            'operationName': 'CreateBasket',
            }
            sess.headers.update(headers)
            sess.cookies.update(cookies)
            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)
            # print(response.status_code)
            # print(response.text)
            jwt = response.headers['jwt']
            headers['authorization'] =f"Bearer {jwt}"
            basket_id = response.json()['data']['createBasket']['id']
            sess.headers.update(headers)
            
            json_data = {
                'query': 'mutation CreateBooking($basketId: String, $createBooking: CreateBookingInput!, $culture: String!) {\n  createBooking(basketId: $basketId, createBooking: $createBooking, culture: $culture) {\n    ...BasketCommon\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                    'createBooking': {
                        'adults': int(adult),
                        'children': int(child),
                        'infants': int(infant),
                        'teens': int(teen),
                        'flights': [
                            {
                                'fareKey': fare_key,
                                'flightKey': flight_key,
                                'fareOption': 'SURE',
                                'offerKeys': [
                                    'LBOYRRI3YS6ZSH5CXN2XBJ4GGYYNZQZASO3QMMM5LITWONAMBC3YN3UD2QGFYZDC6AW5I6ILK53DHB6T6YOFJBVN6B3225MM2ONMFAOLOE64VO7JOWQB34DPTD2TKOIZSZHIBM3APCMVWFZGU5XLTROCDQHNYEQVTLYCO46DJORWB7T6NUK5QDYSOO64GX4C4EIP2XN5ERV4KTVRPQIKQW3CTCETIPT4BTP7YO45U76AHZU232GOD4RNGLJGCJ3BATX7O5ZHKP4QD3ECMFVLVRX5A7S2BDUGBGVLDJKDIRRD36A755BJXWRRN2TFRZSSH44T3FUCDTRAMFZBQSUMMPKKGLXZS342LCA5SWZMXPO2H7PQXGYRER2D2LEWREUVJ23QUILJ2P5DGUXQZXEVB6S5ZA',
                                ],
                            },
                        ],
                        'discount': 0,
                        'promoCode': '',
                        'separateBundle': False,
                    },
                    'culture': locale,
                },
                'operationName': 'CreateBooking',
            }

            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)


            json_data = {
                'query': 'mutation CommitBooking($basketId: String!) {\n  commitBooking(basketId: $basketId) {\n    ...BasketCommon\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                },
                'operationName': 'CommitBooking',
            }
            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)



            json_data = {
                'query': 'query GetBasket($basketId: String!) {\n  basket(id: $basketId) {\n    ...BasketCommon\n    gettingAround {\n      ...GettingAroundPillar\n    }\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\nfragment VariantCar on VariantUnionType {\n  ... on Car {\n    rentPrice\n    carName\n    refId\n    engineLoadId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    extras {\n      totalPrice\n      includedInRate\n      code\n      price\n      selected\n      type\n    }\n    residence\n    age\n  }\n}\n\nfragment VariantCarRental on VariantUnionType {\n  ... on CarRental {\n    rentPrice\n    carName\n    clientId\n    refId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    insuranceQuoteReference\n    extras {\n      code\n      includedInRate\n      payNow\n      price\n      selected\n      totalPrice\n      type\n    }\n    residence\n    age\n    language\n    searchId\n    supplier\n  }\n}\n\nfragment GettingAroundPillar on GettingAroundType {\n  price {\n    amount\n    discount\n    amountWithTaxes\n    total\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  taxes {\n    amount\n  }\n  components {\n    ...ComponentCommon\n    payLater {\n      amountWithTaxes\n      total\n    }\n    variant {\n      ...VariantCar\n      ...VariantCarRental\n      ...VariantGroundTransfer\n    }\n  }\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                },
                'operationName': 'GetBasket',
            }

            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)
        

            json_data = {
                'query': 'query Products($basketId: String!, $productQuery: ProductQuery!, $isCheckInFlow: Boolean!) {\n  products(basketId: $basketId, productQuery: $productQuery) {\n    bags: bag {\n      ...BagFrag\n    }\n    equipments: equipment {\n      ...EquipmentFrag\n    }\n    flightExtras: flightExtra {\n      ...ExtraFrag\n    }\n    priorityBoarding {\n      ...PriorityBoardingFrag\n    }\n  }\n  excessBag(basketId: $basketId, isCheckInFlow: $isCheckInFlow) {\n    code\n    price\n    paxType\n    paxNum\n    journeyNum\n    maxPerPassenger\n    maxPerBag\n  }\n}\n\nfragment BagFrag on Bag {\n  journeyNum\n  maxPerPassenger\n  offers {\n    ...BagOfferFrag\n  }\n}\n\nfragment BagOfferFrag on BagOffer {\n  code\n  maxPerPassenger\n  price {\n    ...BagOfferPriceFrag\n  }\n}\n\nfragment BagOfferPriceFrag on BagOfferPrice {\n  discountPercentage\n  discountType\n  originalPrice\n  paxType\n  total\n  totalDiscount\n  strikeThrough\n}\n\nfragment EquipmentFrag on Equipment {\n  journeyNum\n  offers {\n    code\n    type\n    maxPerPassenger\n    availableItems\n    prices {\n      paxType\n      total\n    }\n  }\n}\n\nfragment ExtraFrag on FlightExtra {\n  code\n  discountPercentage\n  discountType\n  maxPerPassenger\n  minOriginalPrice\n  minPrice\n  totalDiscount\n  priceDetails {\n    journeyNumber\n    segmentNumber\n    minPrice\n    minOriginalPrice\n    discountType\n    totalDiscount\n    dsc\n  }\n}\n\nfragment PriorityBoardingFrag on PriorityBoarding {\n  code\n  price\n  paxType\n  journeyNumber\n  segmentNumber\n  strikeThrough\n}\n',
                'variables': {
                    'basketId': basket_id,
                    'productQuery': {
                        'productTypes': [
                            'PRIOBRDNG',
                            'CBAG',
                            'BAGS',
                            'EQUIPMENT',
                        ],
                    },
                    'isCheckInFlow': False,
                },
            }

            response = sess.post(f'https://www.ryanair.com/api/catalogapi/{locale}/graphql', json=json_data)
            flight_extras = response.json().get('data', {}).get('products', {}).get('flightExtras', [])
            additional_luggage =[
                {
                    "type": "cabin",
                    "outbound_price": "N/A",
                    "return_price": "N/A",
                    "size": {
                        "dimensions": "40 x 20 x 25 cm and 55 x 40 x 20 cm",
                        "weight": "10Kg"
                    },
                    "bookable_fares": [
                        "Basic",
                        "Plus",
                        "Family Plus"
                    ]
                },
                {
                    "type": "checked",
                    "outbound_price": "N/A",
                    "return_price": "N/A",
                    "size": {
                        "dimensions": "120 x 120 x 80 cm",
                        "weight": "20Kg"
                    },
                    "bookable_fares": [
                        "Basic",
                        "Regular",
                        "Plus",
                        "Family Plus",
                        "Flexi Plus"
                    ]
                },
                {
                    "type": "checked",
                    "outbound_price": "N/A",
                    "return_price": "N/A",
                    "size": {
                        "dimensions": "55 x 40 x 20 cm",
                        "weight": "10Kg"
                    },
                    "bookable_fares": [
                        "Basic",
                        "Regular",
                        "Plus",
                        "Flexi Plus"
                    ]
                }
            ]
            extra_price_map = {}

            for item in flight_extras:
                code = item.get("code")
                price_details = item.get("priceDetails", [])
                price = price_details[0].get("minPrice") if len(price_details) > 0 else None

                if code in {"PRIOBRDNG", "CBAG", "BAGS"}:
                    extra_price_map[code] = price if price is not None else 0.0

            if extra_price_map:
                # --- Update luggage prices based on rules ---
                for luggage in additional_luggage:
                    luggage_type = luggage.get("type")
                    weight = luggage.get("size", {}).get("weight")

                    if luggage_type == "cabin":
                        price = extra_price_map.get("PRIOBRDNG", 0.0)
                        luggage["outbound_price"] = float(price)

                    elif luggage_type == "checked":
                        if weight == "10Kg":
                            price = extra_price_map.get("CBAG", 0.0)
                        elif weight == "20Kg":
                            price = extra_price_map.get("BAGS", 0.0)
                        else:
                            price = 0.0
                        luggage["outbound_price"] = float(price)

                flight['additional_luggage'] = additional_luggage

                break
            else:
                attempt += 1
                if attempt < max_retries:
                    print(f"Retrying... attempt {attempt+1}/{max_retries}")
                    time.sleep(2)  # backoff delay
                else:
                    flight['additional_luggage'] = []
                    print(f"Failed after {max_retries} attempts")
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                print(f"Error: {e}")
                flight['additional_luggage'] = []
            time.sleep(2)

def get_additional_luggage_return(flight, outbound_flight_key, outbound_fare_key, return_flight_key, return_fare_key, locale, adult, teen, child, infant,headers,cookies):

    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            
            sess = requests.Session()
            json_data = {
                'query': 'mutation CreateBasket {\n  createBasket {\n    ...BasketCommon\n    gettingAround {\n      ...GettingAroundPillar\n    }\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\nfragment VariantCar on VariantUnionType {\n  ... on Car {\n    rentPrice\n    carName\n    refId\n    engineLoadId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    extras {\n      totalPrice\n      includedInRate\n      code\n      price\n      selected\n      type\n    }\n    residence\n    age\n  }\n}\n\nfragment VariantCarRental on VariantUnionType {\n  ... on CarRental {\n    rentPrice\n    carName\n    clientId\n    refId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    insuranceQuoteReference\n    extras {\n      code\n      includedInRate\n      payNow\n      price\n      selected\n      totalPrice\n      type\n    }\n    residence\n    age\n    language\n    searchId\n    supplier\n  }\n}\n\nfragment GettingAroundPillar on GettingAroundType {\n  price {\n    amount\n    discount\n    amountWithTaxes\n    total\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  taxes {\n    amount\n  }\n  components {\n    ...ComponentCommon\n    payLater {\n      amountWithTaxes\n      total\n    }\n    variant {\n      ...VariantCar\n      ...VariantCarRental\n      ...VariantGroundTransfer\n    }\n  }\n}\n\n',
                'operationName': 'CreateBasket',
            }
            sess.headers.update(headers)
            sess.cookies.update(cookies)
            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)
            jwt = response.headers['jwt']
            headers['authorization'] =f"Bearer {jwt}"
            basket_id = response.json()['data']['createBasket']['id']
            sess.headers.update(headers)
            json_data = {
                'query': 'mutation CreateBooking($basketId: String, $createBooking: CreateBookingInput!, $culture: String!) {\n  createBooking(basketId: $basketId, createBooking: $createBooking, culture: $culture) {\n    ...BasketCommon\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                    'createBooking': {
                        'adults': int(adult),
                        'children': int(child),
                        'infants': int(infant),
                        'teens': int(teen),
                        'flights': [
                            {
                                'fareKey': outbound_fare_key,
                                'flightKey': outbound_flight_key,
                                'fareOption': 'SURE',
                                'offerKeys': [
                                    'BX36E5LP3INPH5JSDYKICF7AIHIDFPPM55LWRNGW3MHB7Q3R4WMPGJ4ZLDPFXZHCDDRIKLS2PWDRPTTUNPCLMHFPDLH3IRDZUZ5AQHTJ23NSSTRX6ELHE7PSRLRRNX3YDBI4EKLNJV2DXPDL25FE3BTHOD35X7FJLPYY37XYOJZXKHBHT6HJI6Z4F7BIWDWNMJZ26OX5AIH6UQCB6GMHBIUYWWMLNVTIK3HHHKL4XFPIOWB2DIBB4YSYJ74RJEXFYPEHV4IAXN33QWUW3ZT2YSVPKGFXI2R326POBYTY2MAKCQZJYGJ4FV3YRM5AQG3SC4WJEUP3FK4KCS4NQHBCYP3CUJYHFELJXQ62EYSH2P5IXPABGS3EN4R3476DM6HCNAVHG3AI5JHGNGEVTCITUKN6VY',
                                ],
                            },
                            {
                                'fareKey': return_fare_key,
                                'flightKey': return_flight_key,
                                'fareOption': 'SURE',
                                'offerKeys': [
                                    'BX36E5LP3INPH5JSDYKICF7AIGCPJQHBYRJFH5YATLJD45LTZCUZKECXAUGQZTQS6HW52KDUT4URWY3IOTCBRUA3UDUEDPPQHE3JZVXL45OEJK2W2TDZ6LG7ULURIAIJ4VM6ZRLX6AJQGTEA42ZSCCL64KWC74VGHDTIA7AWPBRHB66YCICC7VZ6RKN3GVFPOOHH27VSGL7PM2I6XOETH4T5ZSYGFIGX46IB3TYRIM5XZIIOGRBFIINZ7MRXL3CM4J7YIOKASDTUZT6HLUL7EEUF3QXM5YPLNIGCNHR6U2WVKP5OLXEFT23OEWDNMVIUOT7RVG3WOBOGWF7IDJTMARC355TJRJXZTPWNHLGKNVFLSA5UCMVSND6WSQC3X7Y5UI7JQQ22ZZ6EWZWZJJZS66Z36I',
                                ],
                            },
                        ],
                        'discount': 0,
                        'promoCode': '',
                        'separateBundle': False,
                    },
                    'culture': locale,
                },
                'operationName': 'CreateBooking',
            }

            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)

            json_data = {
                'query': 'mutation CommitBooking($basketId: String!) {\n  commitBooking(basketId: $basketId) {\n    ...BasketCommon\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                },
                'operationName': 'CommitBooking',
            }

            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql',  json=json_data)

            json_data = {
                'query': 'query GetBasket($basketId: String!) {\n  basket(id: $basketId) {\n    ...BasketCommon\n    gettingAround {\n      ...GettingAroundPillar\n    }\n  }\n}\n\n\nfragment TotalCommon on PriceType {\n  total\n}\n\nfragment PriceCommon on PriceType {\n  amountWithTaxes\n  total\n  discount\n  discountCode\n}\n\nfragment ComponentCommon on ComponentType {\n  id\n  parentId\n  code\n  type\n  quantity\n  removable\n  hidden\n  price {\n    ...PriceCommon\n  }\n}\n\nfragment VariantUnionAddOn on VariantUnionType {\n  ... on AddOn {\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionFare on VariantUnionType {\n  ... on Fare {\n    fareOption\n    journeyNumber\n  }\n}\n\nfragment VariantUnionSsr on VariantUnionType {\n  ... on Ssr {\n    journeyNumber\n    paxNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionSeat on VariantUnionType {\n  ... on Seat {\n    paxNumber\n    journeyNumber\n    segmentNumber\n    seatType\n    designator\n    childSeatsWithAdult\n    hasAdditionalSeatCost\n    primeIncluded\n  }\n}\n\nfragment VariantUnionBundle on VariantUnionType {\n  ... on Bundle {\n    journeyNumber\n    segmentNumber\n  }\n}\n\nfragment VariantUnionParkingAddOn on VariantUnionType {\n  ... on ParkingAddOn {\n    carParkName\n    itemId\n    provider\n    paxNumber\n    pax\n    src\n    start\n    end\n  }\n}\n\nfragment VariantUnionVoucher on VariantUnionType {\n  ... on Voucher {\n    firstName\n    lastName\n    email\n  }\n}\n\nfragment VariantUnionPhysicalVoucher on VariantUnionType {\n  ... on PhysicalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    scheduleDate\n    message\n  }\n}\n\nfragment VariantUnionDigitalVoucher on VariantUnionType {\n  ... on DigitalVoucher {\n    sequenceNumber\n    firstName\n    lastName\n    email\n    theme\n    scheduleDate\n    scheduleTime\n    message\n  }\n}\n\nfragment VariantUnionPhysicalVoucherShippingAddress on VariantUnionType {\n  ... on PhyscialVoucherShippingAddress {\n    address1\n    address2\n    city\n    postalCode\n    country\n    countryName\n    firstName\n    lastName\n  }\n}\n\nfragment VariantUnionChangePaxType on VariantUnionType {\n  ... on ChangePassengerType {\n    passengerNumber\n    invalidJourneys {\n      journeyNumber\n      passengers {\n        passengerNumber\n        passengerType\n      }\n    }\n    mandatorySeatPricesWithoutDiscount {\n      journeyNumber\n      passengerNumber\n      feePriceWithoutDiscount\n      cost\n    }\n  }\n}\n\nfragment VariantUnionAddInfant on VariantUnionType {\n  ... on AddInfant {\n    journeyNumber\n    invalidPassengers {\n      passengerNumber\n      passengerType\n    }\n    segmentNumber\n    paxNumber\n  }\n}\n\nfragment VariantGroundTransfer on VariantUnionType {\n  ... on GroundTransfer {\n    locationPickUp\n    locationDropOff\n    routeType\n    startDate\n    endDate\n    itemId\n    location\n  }\n}\n\nfragment GettingTherePillar on GettingThereType {\n  isPrime\n  price {\n    ...TotalCommon\n  }\n  journeys {\n    ... on JourneyType {\n      arrival\n      departure\n      destination\n      duration\n      fareClass\n      fareKey\n      fareOption\n      flightKey\n      flightNumber\n      isConnecting\n      isDomestic\n      journeyNum\n      origin\n      changeInfo {\n        ... on ChangeInfoType {\n          isChangeable\n          freeMove\n          isChanged\n        }\n      }\n      segments {\n        ... on SegmentType {\n          aircraft\n          arrival\n          departure\n          destination\n          duration\n          hasGovernmentTax\n          flightNumber\n          segmentNum\n          origin\n          originCountry\n          destinationCountry\n        }\n      }\n    }\n  }\n  discounts {\n    ... on DiscountType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n      description\n      qty\n    }\n  }\n  taxes {\n    ... on TaxType {\n      amount\n      code\n      journeyNum\n      percentage\n      zone\n    }\n  }\n  vouchers {\n    ... on VoucherType {\n      amount\n      code\n      status\n      accountNumber\n      voucherBasisCode\n    }\n  }\n  components {\n    ... on ComponentType {\n      ...ComponentCommon\n      variant {\n        ...VariantUnionAddOn\n        ...VariantUnionFare\n        ...VariantUnionSsr\n        ...VariantUnionSeat\n        ...VariantGroundTransfer\n        ...VariantUnionBundle\n        ...VariantUnionParkingAddOn\n        ...VariantUnionVoucher\n        ...VariantUnionDigitalVoucher\n        ...VariantUnionPhysicalVoucher\n        ...VariantUnionPhysicalVoucherShippingAddress\n        ...VariantUnionChangePaxType\n        ...VariantUnionAddInfant\n      }\n    }\n  }\n  messages {\n    ... on MessageType {\n      type\n      journeyNum\n      key\n      message\n    }\n  }\n}\n\nfragment PayLaterCommon on PriceType {\n  total\n}\n\nfragment BasketCommon on BasketType {\n  id\n  tripId\n  dotrezSessionId\n  currency\n  gettingThere {\n    ...GettingTherePillar\n  }\n  price {\n    ...TotalCommon\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  totalToPay\n}\n\nfragment VariantCar on VariantUnionType {\n  ... on Car {\n    rentPrice\n    carName\n    refId\n    engineLoadId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    extras {\n      totalPrice\n      includedInRate\n      code\n      price\n      selected\n      type\n    }\n    residence\n    age\n  }\n}\n\nfragment VariantCarRental on VariantUnionType {\n  ... on CarRental {\n    rentPrice\n    carName\n    clientId\n    refId\n    pickUpTime\n    pickUpLocation {\n      countryCode\n      code\n      name\n    }\n    dropOffTime\n    dropOffLocation {\n      countryCode\n      code\n      name\n    }\n    insurance\n    insuranceQuoteReference\n    extras {\n      code\n      includedInRate\n      payNow\n      price\n      selected\n      totalPrice\n      type\n    }\n    residence\n    age\n    language\n    searchId\n    supplier\n  }\n}\n\nfragment GettingAroundPillar on GettingAroundType {\n  price {\n    amount\n    discount\n    amountWithTaxes\n    total\n  }\n  payLater {\n    ...PayLaterCommon\n  }\n  taxes {\n    amount\n  }\n  components {\n    ...ComponentCommon\n    payLater {\n      amountWithTaxes\n      total\n    }\n    variant {\n      ...VariantCar\n      ...VariantCarRental\n      ...VariantGroundTransfer\n    }\n  }\n}\n\n',
                'variables': {
                    'basketId': basket_id,
                },
                'operationName': 'GetBasket',
            }

            response = sess.post(f'https://www.ryanair.com/api/basketapi/{locale}/graphql', json=json_data)

            json_data = {
                'query': 'query Products($basketId: String!, $productQuery: ProductQuery!, $isCheckInFlow: Boolean!) {\n  products(basketId: $basketId, productQuery: $productQuery) {\n    bags: bag {\n      ...BagFrag\n    }\n    equipments: equipment {\n      ...EquipmentFrag\n    }\n    flightExtras: flightExtra {\n      ...ExtraFrag\n    }\n    priorityBoarding {\n      ...PriorityBoardingFrag\n    }\n  }\n  excessBag(basketId: $basketId, isCheckInFlow: $isCheckInFlow) {\n    code\n    price\n    paxType\n    paxNum\n    journeyNum\n    maxPerPassenger\n    maxPerBag\n  }\n}\n\nfragment BagFrag on Bag {\n  journeyNum\n  maxPerPassenger\n  offers {\n    ...BagOfferFrag\n  }\n}\n\nfragment BagOfferFrag on BagOffer {\n  code\n  maxPerPassenger\n  price {\n    ...BagOfferPriceFrag\n  }\n}\n\nfragment BagOfferPriceFrag on BagOfferPrice {\n  discountPercentage\n  discountType\n  originalPrice\n  paxType\n  total\n  totalDiscount\n  strikeThrough\n}\n\nfragment EquipmentFrag on Equipment {\n  journeyNum\n  offers {\n    code\n    type\n    maxPerPassenger\n    availableItems\n    prices {\n      paxType\n      total\n    }\n  }\n}\n\nfragment ExtraFrag on FlightExtra {\n  code\n  discountPercentage\n  discountType\n  maxPerPassenger\n  minOriginalPrice\n  minPrice\n  totalDiscount\n  priceDetails {\n    journeyNumber\n    segmentNumber\n    minPrice\n    minOriginalPrice\n    discountType\n    totalDiscount\n    dsc\n  }\n}\n\nfragment PriorityBoardingFrag on PriorityBoarding {\n  code\n  price\n  paxType\n  journeyNumber\n  segmentNumber\n  strikeThrough\n}\n',
                'variables': {
                    'basketId': basket_id,
                    'productQuery': {
                        'productTypes': [
                            'PRIOBRDNG',
                            'CBAG',
                            'BAGS',
                            'EQUIPMENT',
                        ],
                    },
                    'isCheckInFlow': False,
                },
            }

            response = sess.post(f'https://www.ryanair.com/api/catalogapi/{locale}/graphql',  json=json_data)
            flight_extras = response.json().get('data', {}).get('products', {}).get('flightExtras', [])
            additional_luggage =[
            {
                "type": "cabin",
                "outbound_price": "N/A",
                "return_price": "N/A",
                "size": {
                    "dimensions": "40 x 20 x 25 cm and 55 x 40 x 20 cm",
                    "weight": "10Kg"
                },
                "bookable_fares": [
                    "Basic",
                    "Plus",
                    "Family Plus"
                ]
            },
            {
                "type": "checked",
                "outbound_price": "N/A",
                "return_price": "N/A",
                "size": {
                    "dimensions": "120 x 120 x 80 cm",
                    "weight": "20Kg"
                },
                "bookable_fares": [
                    "Basic",
                    "Regular",
                    "Plus",
                    "Family Plus",
                    "Flexi Plus"
                ]
            },
            {
                "type": "checked",
                "outbound_price": "N/A",
                "return_price": "N/A",
                "size": {
                    "dimensions": "55 x 40 x 20 cm",
                    "weight": "10Kg"
                },
                "bookable_fares": [
                    "Basic",
                    "Regular",
                    "Plus",
                    "Flexi Plus"
                ]
            }
        ]
            extra_price_map = {}
            for item in flight_extras:
                code = item.get("code")
                price_details = item.get("priceDetails", [])

                if len(price_details) >= 1:
                    outbound_price = price_details[0].get("minPrice", "N/A")
                    return_price = price_details[1].get("minPrice", "N/A") if len(price_details) >= 2 else "N/A"

                    if outbound_price is not None and return_price is not None:
                        extra_price_map[code] = f"{outbound_price},{return_price}"

            
            if extra_price_map:
                # --- Update luggage prices based on rules ---
                for luggage in additional_luggage:
                    luggage_type = luggage.get("type")
                    weight = luggage.get("size", {}).get("weight")

                    if luggage_type == "cabin":
                        prices = extra_price_map.get("PRIOBRDNG", "0,0").split(',')
                        outbound = prices[0] if prices[0] != "N/A" else 0.0
                        ret = prices[1] if prices[1] != "N/A" else 0.0
                        luggage["outbound_price"] = float(outbound)
                        luggage["return_price"] = float(ret)

                    elif luggage_type == "checked":
                        if weight == "10Kg":
                            prices = extra_price_map.get("CBAG", "0,0").split(',')
                        elif weight == "20Kg":
                            prices = extra_price_map.get("BAGS", "0,0").split(',')

                        outbound = prices[0] if prices[0] != "N/A" else 0.0
                        ret = prices[1] if prices[1] != "N/A" else 0.0
                        luggage["outbound_price"] = float(outbound)
                        luggage["return_price"] = float(ret)

                flight['additional_luggage'] = additional_luggage
                break
            else:
                attempt += 1
                if attempt < max_retries:
                    print(f"Retrying... attempt {attempt+1}/{max_retries}")
                    time.sleep(2)  # backoff delay
                else:
                    flight['additional_luggage'] = []
                    print(f"Failed after {max_retries} attempts")

        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                print(f"Error: {e}")
                flight['additional_luggage'] = []
            time.sleep(2)
        
def get_flight_key_oneway(data,locale,adult,teen,child,infant):
    try:
        # headers = header
        threads = []
        # flight_extras_list = []
        headers = header()
        cookies = cookie()
        for flight in data[0].get("flights", []):
            outbound = flight.get("outbound", {})
            flight_key = outbound.get("flight_key")
            fare_key = outbound.get("fare_key")
            
            # Create a new session for each thread
        
            # sess.headers.update(headers)
            
            thread = threading.Thread(
                target=get_addtional_luggage_oneway,
                args=(flight,flight_key,fare_key,locale,adult,teen,child,infant,headers,cookies)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        return data
    except Exception as e:
        print(f"Error: {e}")
        return {"status":500,"Error":"Internal Server Error"}

def get_flight_key_return(data,locale,adult,teen,child,infant):
    try:
        
        threads = []
        # flight_extras_list = []
        cookies = cookie()
        headers = header()
        for flight in data.get("flights", []):
            outbound = flight.get("outbound", {})
            outbound_flight_key = outbound.get("flight_key")
            outbound_fare_key = outbound.get("fare_key")
            return_info = flight.get("return", {})
            return_flight_key = return_info.get("flight_key")
            return_fare_key = return_info.get("fare_key")
            # Create a new session for each thread
            
            # sess.headers.update(headers)
            
            thread = threading.Thread(
                target=get_additional_luggage_return,
                args=(flight,outbound_flight_key,outbound_fare_key,return_flight_key,return_fare_key,locale,adult,teen,child,infant,headers,cookies)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        return data
    except Exception as e:
        # print(f"Error: {e}")
        return {"status":500,"Error":"Internal Server Error"}
def get_flight_info(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,roundtrip_check):
    if roundtrip_check=="QUERY_TYPE_RETURN":
        st = time.time()
        trip="true"
        result , passenger_count= get_return_flight(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,trip)
        if 'Error' in result:
            return result
        data = create_flight_combinations(result,passenger_count,adult,teen,child,infant,locale)
        if not data:
            return {"status": 404, "Error": "flights are not available"}
        print(time.time()-st)
        final_data = get_flight_key_return(data,locale,adult,teen,child,infant)
        return final_data
    if roundtrip_check=="QUERY_TYPE_ONE_WAY":
        trip="false"
        datein=""
        data= get_oneway_flight(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,trip)
        if not data:
            return {"status": 404, "Error": "flights are not available"}
        elif 'Error' in data:
            return data
        final_data = get_flight_key_oneway(data,locale,adult,teen,child,infant)
        return final_data

if __name__ == "__main__":
    adult="3"
    teen="0"
    child="0"
    infant="0"
    origin="BGY"
    destinaiton="MAH"
    dateout="2025-08-14"
    datein="2025-08-17"
    locale ="it-IT"
    roundtrip_check="QUERY_TYPE_ONE_WAY"
    import time
    start=time.time()
    data = get_flight_info(adult,teen,child,infant,origin,destinaiton,dateout,datein,locale,roundtrip_check)
    with open("return_flight.json", "w") as f:
        json.dump(data, f)
    print(time.time()-start)