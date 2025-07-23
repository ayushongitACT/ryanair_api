from pymongo import MongoClient
def get_headers():
    return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'client': 'desktop',
            'client-version': '3.148.0',
            'newrelic': 'eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjY0NjgzMiIsImFwIjoiMjgxMjk3Njk4IiwiaWQiOiI5YWM5OTc2OGNkOTg3MDYxIiwidHIiOiJlY2YwNmZmZmQ2NDhkYjdmOTkzYzllMzkxMmVmZmMyNyIsInRpIjoxNzQ3ODEzNTQxNzE4fX0=',
            'priority': 'u=1, i',
            'referer': 'https://www.ryanair.com/us/en/trip/flights/select?adults=1&teens=1&children=1&infants=0&dateOut=2025-05-29&dateIn=2025-05-30&isConnectedFlight=false&discount=0&isReturn=false&promoCode=&originIata=LBA&destinationIata=DUB&tpAdults=1&tpTeens=1&tpChildren=1&tpInfants=0&tpStartDate=2025-05-29&tpEndDate=2025-05-30&tpDiscount=0&tpPromoCode=&tpOriginIata=LBA&tpDestinationIata=DUB',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'traceparent': '00-ecf06fffd648db7f993c9e3912effc27-9ac99768cd987061-01',
            'tracestate': '646832@nr=0-1-646832-281297698-9ac99768cd987061----1747813541718',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'x-flight-search-token': '47QFO2ADVUGTO7SXYMOMBIYSWPOPDI5GAYRITLNIBLDLEAJYWZIWNSHS5QR7P7GGY5DUVDLECLHBLZRERBN5MKZ3OB7YCXLDBLXB2WYB2Z4MTVT2ELO6HMT3OJUJKTUMNAIDMIQIFM7TQG6AK5LRAA6CR2Z6A37EIMWOPZ6BQSEBG5Y6L7HYOMOTNMNZ65RYDIL3266D4FQYKJVSQXHCLDMIICU7RAW7EOKWCXVFB6QQOZ72WQBJJRCH7CNZR4Y3LIYV5TAWH4TFKCDWCQS3HXIP5BMVXI7UP44E6I4UB36BJD7NDSOR2VBG7BEBOKTNXGDMGI46PCJGSPBTXAOXQARP2FND725W7AY4XR44NOQXPPFHKWDHGE4CWGCME5ID',
            # 'cookie': 'mkt=/us/en/; STORAGE_PREFERENCES={"STRICTLY_NECESSARY":true,"PERFORMANCE":false,"FUNCTIONAL":false,"TARGETING":false,"SOCIAL_MEDIA":false,"PIXEL":false,"__VERSION":4}; xid=39a2c0f1-679f-4008-82a8-8c40e635386a; rid.sig=jyna6R42wntYgoTpqvxHMK7H+KyM6xLed+9I3KsvYZaVt7P36AL6zp9dGFPu5uVxaIiFpNXrszr+LfNCdY3IT3oCSYLeNv/ujtjsDqOzkY5JmUFsCdAEz3kpPbhCUwiArp5oaa75tpJtO3kFwYQ8l0DbH67AtcN/PMbniLsiM5qn+2AjrrtoNJicE3ZQwFHVipe4lWPSRfq2OIyUrlFhwEDt20+wCX7l1mCubNXtG6nZrUA07sFUFhn4RUxnjwjJ6d9qjjBasXLvYSqyYN7UaY8s+X70korZyaicZWcWTvN/flT6mVrazE0dZgQcqxwrQuYmS/JbjTlBUP9laFOeN4g6Mzc13dsXUVTiubbd5H0T2XIo2pi2hTkIMhRKOD4SWe1Gz8obpJBiLx1+YU0FBV9XWfS7YpXjscKQjtzcI0NJ9qONIpGD8WmUoKEX4nNPvcbHiroR2ciIuDNn7GN+E72kkN3j+Q8cAVcHMKW5eWOuETlOS2/2u2G4Vcn7Pao7AzLiwmnC8HpLO8+Y0H79VbEeoZbZrF2+KlDA/QAniV8AoLOzKSxVNUl2WaksKPO8gyF81kTmdeO8UlesnCOgUfymszXJliby3M4E7J8en/u944nJJR2NsfHNszvQf3TKw5O4cwkyCesOhfm+ek/SbVFVAkUJFzlcaf/KL50RzR6j/FXZkFp0e3KvcPOURYNT8j67eWi6QJEJpK+2GFvHbxuUgG8fmucv3qG/CsnBLxMeFWHqctli3oFK6UPZZfGc84a4LnHVdP3SBPdhc9ASG1gnrc0xhWPekpgE+qx3PYYk9LGqIioCcO2HydyenKy2; rid=cc96a1b8-8e75-42ab-8299-afff5c128ea7; fr-correlation-id=09dc6b37-48e3-4460-827e-daaff37d5cb5',
        }

def get_cookies():
    client = MongoClient("mongodb://actowiz:tvvL4n%3D33%3D*_@51.222.244.92:27017/admin?authSource=admin")

    db = client["ryanair_api"]
    collection = db["cookies"]

    doc = collection.find_one()

    cookie_dict = doc["cookies"] if doc and "cookies" in doc else {}
    return cookie_dict