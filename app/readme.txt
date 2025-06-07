python manage.py runserver


Call This Every 15 Min (Scheduler Ready)
GET http://localhost:8000/api/fetch-latest-15min/?symbol=EURUSD

2025 data
http://localhost:8000/api/fetch-2025/?symbol=EURUSD

fetch data from to
POST http://localhost:8000/api/fetch-15min/
Body:
{
  "symbol": "EURUSD",
  "from": "2025-03-01",
  "to": "2025-03-07"
}

