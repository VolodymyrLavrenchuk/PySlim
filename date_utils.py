from datetime import datetime as d, timedelta
import json
import time
import re


class DateUtils:

    def mongo_date(self, str):
        return d.strptime("%d %s" % (d.now().year, str),"%Y %a %b %d %H:%M:%S")

    def es_date(self, str):
        return d.strptime(str, "%Y-%m-%d %H:%M:%S,%f")
    
    def express_date(self, str):
        return d.strptime(str, "%Y-%m-%d %H:%M:%S.%f")

    def nowUtc(self):
        return d.utcnow()
    

    def now(self):
        return d.now()
        
    def nowDate(self):
        return self.now().date()
    
    def nowTime(self):
        return self.now().time()

    def nowIso(self):
        return self.now().isoformat()
        
    def addSecondsTo(self,sec, dt):
        return d.strptime(dt, "%Y-%m-%d %H:%M:%S.%f") + timedelta(seconds = int(sec))

    def dateInRange(self, dt, left, right):
        dtDate = d.strptime(dt, "%Y-%m-%dT%H:%M:%S.%fZ")
        return (dtDate >= d.strptime(left, "%Y-%m-%d %H:%M:%S.%f")) and (dtDate <= d.strptime(right, "%Y-%m-%d %H:%M:%S.%f"))

    def getLocalTimeZone(self):

      offset = int( round( ( d.now() - d.utcnow() ).total_seconds() ) ) / 60 / 60

      if offset >= 0:
        return "+" + str( offset ) + "00"
      else:
        return offset

    def js_time_diff( self, js_time, unix_time = None ):

        match = re.match( '\/Date\((\d+)\)\/', js_time )
        js_t = match.group( 1 ) if match else 0
        u_t = unix_time if unix_time else time.time()
        return int( u_t * 1000 ) - int( js_t )

    def DemoMode(self,val):
        time.sleep(int(val))
