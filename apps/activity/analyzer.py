from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytz
from dateutil.relativedelta import relativedelta

from apps.account.models import Athlete
from apps.activity.models import Activity


class SingleAnalyzer():

    def __init__(self, activity_id: int):
        self.activity = Activity.objects.get(id=activity_id)
        self.athlete = Athlete.objects.get(id=self.activity.athlete_id)

    def analyze(self):
        # We only do heart rate base analytics for now
        if self.activity.detail.get('has_heartrate'):
            self.init_metrics()
            self.init_df()
            hrss = self.calculate_heartrate_stress_score()
            return {"hrss": hrss}

        return {}

    def init_metrics(self):
        self.trimp_factor = 1.92 if self.athlete.sex.upper() == 'M' else 1.67

        age = relativedelta(datetime.today(), self.athlete.birthday).years
        self.hr_max = 220 - age
        self.hr_min = self.athlete.resting_hr

    def init_df(self):
        # Which streams will be analyzed
        types = ['time', 'heartrate']

        self.df = pd.DataFrame(columns=types)
        for type in types:
            self.df[type] = pd.Series(self.activity.streams[type]["data"], index=None)

        # Add timestamp col
        self.df['start_date'] = self.activity.start_date
        self.df['timestamp'] = pd.Series(map(
            lambda s, d: d + timedelta(seconds=int(s)),
            self.df['time'], self.df['start_date']))
        self.df.set_index('timestamp', inplace=True)

        # Resample
        self.df = self.df.resample('1S').mean()
        self.df = self.df.interpolate(limit_direction='both')

    def calculate_heartrate_stress_score(self):
        athlete_lthr = ((self.hr_max - self.hr_min) * 0.85) + self.hr_min  # Karvonen formula

        self.df['hrr'] = self.df['heartrate'].apply(lambda x: (x - self.hr_min) / (self.hr_max - self.hr_min))

        self.trimp = ((1 / 60) * self.df['hrr'] * (
            0.64 * np.exp(self.trimp_factor * self.df['hrr']))).sum()

        athlete_hrr_lthr = (athlete_lthr - self.hr_min) / (self.hr_max - self.hr_min)
        hrss = (self.trimp / (60 * athlete_hrr_lthr * (0.64 * np.exp(self.trimp_factor * athlete_hrr_lthr)))) * 100

        return hrss


class ProgressAnalyzer():

    def __init__(self, user_id):
        self.user_id = user_id

    def analyze(self):
        last_year = datetime.today() - timedelta(days=366)
        user_activities = Activity.objects.filter(
            user_id=self.user_id,
            start_date__gte=last_year,
        ).order_by('start_date')

        last = user_activities.last()
        timezone = last.timezone if last else "UTC"

        today = datetime.now().astimezone(pytz.timezone(timezone))
        last_year = today - timedelta(days=366)

        user_analytics = user_activities.values("analytics", "start_date_local")

        if len(user_analytics):
            self.df = pd.DataFrame(user_analytics)
            return self.calculate_fitness_performance()

        return {}

    def calculate_fitness_performance(self):
        atl_days = 7
        ctl_days = 42

        # Index by date to resample
        self.df['date'] = pd.to_datetime(self.df['start_date_local'], utc=True)
        self.df.set_index('date', inplace=True)

        # Use hrss as stress_score
        self.df['hrss'] = self.df["analytics"].map(lambda a: a.get('hrss', 0) if type(a) is dict else 0).fillna(0)
        self.df['stress_score'] = self.df['hrss']
        self.df = self.df[['stress_score']].resample('D').sum()

        # Calculate perf.
        self.df['ctl'] = self.df['stress_score'].rolling(ctl_days, min_periods=1).mean()
        self.df['atl'] = self.df['stress_score'].rolling(atl_days, min_periods=1).mean()
        self.df['tsb'] = self.df['ctl'] - self.df['atl']

        self.df.drop(['stress_score'])
        return self.df.to_dict(orient="index")