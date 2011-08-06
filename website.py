#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.


import os
import json
import os
import sys
from twisted.web import server, resource

def flat_info(request, bithopper_global):
     response = '<html><head><title>bitHopper Info</title></head><body>'
     current_name = bithopper_global.pool.get_entry(bithopper_global.pool.get_current())['name']
     response += '<p>Current Pool: ' + current_name+' @ ' + str(bithopper_global.speed.get_rate()) + 'MH/s</p>'
     response += '<table border="1"><tr><td>Name</td><td>Role</td><td>Shares'
     response += '</td><td>Rejects</td><td>Payouts</td><td>Efficiency</td></tr>'
     servers = bithopper_global.pool.get_servers()
     for server in servers:
          info = servers[server]
          if info['role'] not in ['backup','mine', 'api_disable']:
                continue
          shares = str(bithopper_global.db.get_shares(server))
          rejects = bithopper_global.pool.get_servers()[server]['rejects']
          rejects_str = "{:.3}%".format(float(rejects/(float(shares)+1)*100)) + "(" + str(rejects)+")"
          response += '<tr><td>' + info['name'] + '</td><td>' + info['role'] + \
                             '</td><td>' + shares + \
                             '</td><td>' + rejects_str +\
                             '</td><td>' + str(bithopper_global.db.get_payout(server)) + \
                             '</td><td>' + str(bithopper_global.stats.get_efficiency(server)) \
                             + '</td></tr>'

     response += '</table></body></html>'
     request.write(response)
     request.finish()
     return

class dynamicSite(resource.Resource):
    def __init__(self,bitHopper):
      self.bh = bitHopper
      
    isleaF = True
    def render_GET(self,request):
        index_name = 'index.html'
        try:
          # determine scheduler index.html
          if hasattr(self.bh.scheduler,'index_html'):
               index_name = self.bh.scheduler.index_html
          # determine if application is a script file or frozen exe
          if hasattr(sys, 'frozen'):
                application_path = os.path.dirname(sys.executable)
          elif __file__:
                application_path = os.path.dirname(__file__)          
          index = parser.read(os.path.join(application_path, index_name))
        except:
          index = index_name
        file = open(index, 'r')
        linestring = file.read()
        file.close
        request.write(linestring)
        request.finish()
        return server.NOT_DONE_YET

    def render_POST(self, request):
        for v in request.args:
            if "role" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.pool.get_entry(server)['role'] = request.args[v][0]
                    self.bh.pool.get_entry(server)['refresh_time'] = 60
                    if request.args[v][0] in ['mine','info']:
                      self.bh.pool.update_api_server(server)

                except Exception,e:
                    self.bh.log_msg('Incorrect http post request role')
                    self.bh.log_msg(e)
            if "payout" in v:
                try:
                    server = v.split('-')[1]
                    self.bh.update_payout(server, float(request.args[v][0]))
                except Exception,e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)
            if "penalty" in v:
               try:
                    server = v.split('-')[1]
                    info = self.bh.pool.get_entry(server)
                    info['penalty'] = float(request.args[v][0])                    
                    self.bh.select_best_server()
               except Exception,e:
                    self.bh.log_dbg('Incorrect http post request payout')
                    self.bh.log_dbg(e)

        return self.render_GET(request)

class flatSite(resource.Resource):

     def __init__(self,bitHopper):
          resource.Resource.__init__(self)
          self.bitHopper = bitHopper

     isLeaf = True
     def render_GET(self, request):
          flat_info(request,self.bitHopper)
          return server.NOT_DONE_YET

     #def render_POST(self, request):
     #     global new_server
     #     bithopper_global.new_server.addCallback(bitHopperLP, (request))
     #     return server.NOT_DONE_YET


     def getChild(self,name,request):
          return self

class dataSite(resource.Resource):

     def __init__(self,bitHopper):
          resource.Resource.__init__(self)
          self.bitHopper = bitHopper

     isLeaf = True
     def render_GET(self, request):

          #Slice Info
          if hasattr(self.bitHopper.scheduler, 'sliceinfo'):
            sliceinfo = self.bitHopper.scheduler.sliceinfo
          else:
            sliceinfo = None

          response = json.dumps({
             "current":self.bitHopper.pool.get_current(), 
             'mhash':self.bitHopper.speed.get_rate(), 
             'difficulty':self.bitHopper.difficulty.get_difficulty(),
             'sliceinfo':sliceinfo,
             'servers':self.bitHopper.pool.get_servers(),
             'user':self.bitHopper.data.get_users()})
          request.write(response)
          request.finish()
          return server.NOT_DONE_YET

     #def render_POST(self, request):
     #     bithopper_global.new_server.addCallback(bitHopperLP, (request))
     #     return server.NOT_DONE_YET

class lpSite(resource.Resource):

     def __init__(self,bitHopper):
          resource.Resource.__init__(self)
          self.bitHopper = bitHopper

     isLeaf = True
     def render_GET(self, request):
          self.bitHopper.new_server.addCallback(self.bitHopper.bitHopperLP, (request))
          return server.NOT_DONE_YET

     def render_POST(self, request):
          self.bitHopper.new_server.addCallback(self.bitHopper.bitHopperLP, (request))
          return server.NOT_DONE_YET

class bitSite(resource.Resource):

     def __init__(self,bitHopper):
          resource.Resource.__init__(self)
          self.bitHopper = bitHopper

     def render_GET(self, request):
          self.bitHopper.new_server.addCallback(self.bitHopper.bitHopperLP, (request))
          return server.NOT_DONE_YET

     def render_POST(self, request):
          return self.bitHopper.bitHopper_Post(request)


     def getChild(self,name,request):
          #bithopper_global.log_msg(str(name))
          if name == 'LP':
                return lpSite(self.bitHopper)
          elif name == 'flat':
                return flatSite(self.bitHopper)
          elif name == 'stats' or name == 'index.html':
                return dynamicSite(self.bitHopper)
          elif name == 'data':
                return dataSite(self.bitHopper)
          return self
