import traceback
import lpworkbench

def main(bitHopper):
    try:
        lpWorkbench_instance = lpworkbench.lpWorkbench(bitHopper)
        bitHopper.website.sites.append(lpWorkbench_instance)
        
        lpWorkbenchDataSite_instance = lpworkbench.lpWorkbenchDataSite(bitHopper)
        bitHopper.website.sites.append(lpWorkbenchDataSite_instance)
        
    except Exception, e:
        bitHopper.log_msg('Error logging lpworkbench plugin: ' + str(e))
        if bitHopper.options.debug:
            traceback.print_exc()
            
