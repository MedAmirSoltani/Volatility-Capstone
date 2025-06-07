# mt5data/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from .jobs import fetch_and_save_mt5_data

def scheduled_fetch():
    fetch_and_save_mt5_data()

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # ✅ Use the proper module-level function, not an inline one
    scheduler.add_job(scheduled_fetch, "interval", minutes=15, id="fetch_mt5_job", replace_existing=True)

    register_events(scheduler)
    scheduler.start()
