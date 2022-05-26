from infocyte import hunt_base, target, controller, agent, schedule
import random 
import uuid
import time
import copy
import json
import requests
import gzip
from multiprocessing import Process
import itertools
import os

cnt = controller.ControllerGroups()
tgt = target.Target()
base = hunt_base.BaseRequests()
agt = agent.Agent()
sch = schedule.Schedule()

ts = time.gmtime()
current_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts)

#base.base_url = "https://testhomer19"
#base.api_token = "api token"
process_payload = "/home/homer/Downloads/HostSurvey/process-0000.ndjson.gz"
account_payload = "/home/homer/Downloads/HostSurvey/account-0000.ndjson.gz"
memscan_payload_path = "" #todo
av_payload_path = "" #todo
agent_ids = []
agent_ips = []

def new_target():
    #new target group
    controller_group_request = cnt.get_controller_group_by_field("name", "Controller Group 1")
    controller_group_info = controller_group_request.json()
    controller_group_id = controller_group_info[0]['id']
    print(f"Controller group 1 id: {controller_group_id}")

    target_create_response = tgt.new_target(f"new{random.randint(0, 999)}", controller_group_id)

    if target_create_response.status_code == 200:
        target_info = target_create_response.json()
        target_id = target_info['id']
        sch.continuous_monitoring(target_id)

        return [target_info, target_id, controller_group_id]

    else:
        raise Exception(f"Unexpected status code {target_create_response.status_code}")
    
def register_agent():
    target_data = new_target()
    #new agent registration
    agent_id = str(uuid.uuid1()) 
    agent_ids.append(agent_id)
    agent_ip = "10.10.10." + str(random.randint(0,255))
    agent_ips.append(agent_ip)

    api_endpoint = "/api/agents/register"

    body = {
        "acceptFileJobs": None,
        "currentJob": None,
        "friendlyName": None,
        "hostInfo": {
            "agentId": agent_id,
            "architecture": "64-bit",
            "cpe23Uri": None,
            "domain": "",
            "hostname": "fakehost.int",
            "ip": None,
            "osVersion": "windows 5000",
            "rmmDeviceId": None
        },
        "isInstalled": False,
        "platform": None,
        "token": agent_id
    }

    register_heads = copy.deepcopy(base.base_headers)
    register_heads['ignoreversioning'] = "true"
    register_heads['ligerhash'] = ""
    register_heads['version'] = "2.5.1"

    register_response = base.request_post(api_endpoint, request_headers=register_heads, request_body=body)
    if register_response.status_code == 200:
        resp_agent_id = agent_id
        print(f"agent with id: {agent_id} created")
        response = agt.approve_agent(agent_id)
        assign_agent_tg(agent_id, target_data[1])

        #return [target_data, agent_id, agent_ip]
        #return [agent_heartbeat(agent_id, agent_ip), target_data, agent_id, agent_ip]   
    else:
        raise Exception(f"agent register failure {register_response.status_code}\nresponse body {register_response.json()}")

def assign_agent_tg(agent_id, target_id):
    #assign agent to tg
    tg_assign_response = agt.assign_agent_tg(agent_id, target_id)
    if tg_assign_response.status_code == 200:
        print(f"Agent {agent_id} assigned to target group {target_id}")
    else:
        raise Exception(f"Unexpected response status {tg_assign_response.status_code}")
    """
    print(f"agent {agent_id} succesfully registered and approved. waiting 70s for memcache to catch up")
    time.sleep(70)"""

def agent_heartbeat(agent_id, agent_ip):
    heartbeat_body = {
        "acceptFileJobs": 10,
        "currentJob": None,
        "epp": {
            "defender": {
                "data": {
                    "asSignature": "0.0.0.0",
                    "avSignature": "0.0.0.0",
                    "engine": "0.0.0.0",
                    "fileSystemFilter": "0.0.0.0",
                    "nisEngine": "0.0.0.0",
                    "nisSignature": "0.0.0.0",
                    "product": "4.18.1909.6",
                    "service": "0.0.0.0"
                },
                "enabled": False
            }
        },
        "friendlyName": None,
        "hostInfo": {
            "agentId": agent_id,
            "architecture": "64-bit",
            "cpe23Uri": None,
            "domain": "",
            "hostname": "fakehost.int",
            "ip": agent_ip,
            "osVersion": "windows 5000",
            "rmmDeviceId": None
        },
        "isInstalled": False,
        "metrics": {
            "dbSize": 1040384,
            "ligerInfo": {
                "cpuLoad": 0.009999999776482582,
                "ramUsage": 0.03
            },
            "logDirSize": 2035,
            "queryTimes": {},
            "stats": {
                "apiFailures": 0,
                "downloadFailures": 0,
                "uploadFailures": 0
            },
            "systemInfo": {
                "cpuCores": 2,
                "cpuLoad": 0,
                "ramUsage": 60,
                "totalRam": 4095,
                "updating": False,
                "usedRam": 2470
            }
        },
        "platform": "windows64",
        "token": agent_id
    }

    heartbeat_endpoint = "/api/agents/heartbeat"
    heartbeat_heads = copy.deepcopy(base.base_headers)
    heartbeat_heads['ignoreversioning'] = "true"
    heartbeat_heads['ligerhash'] = ""
    heartbeat_heads['version'] = "2.5.1.332"


    job_info = []
    while job_info == []:
        response = base.request_post(heartbeat_endpoint, request_headers=heartbeat_heads, request_body=heartbeat_body)
        heartbeat_response = response.json()
        try:
            job_info = heartbeat_response['jobs'][0]
            print(job_info)

        except IndexError:
            print("no job info sleeping")
            time.sleep(5)
            continue

    comp_url = f"{base.base_url}/api/agents/completejob"
    comp_heads = {"authorization":f"agent {agent_id}", "content-type":"application/json", "job":f"{job_info['id']}", "version":"2.5.1"}
    complete_job_response = requests.post(comp_url, headers=comp_heads, data=json.dumps({"message": "job complete"}))

    return job_info

def mock_rts():

    for (a, b) in itertools.zip_longest(agent_ids, agent_ips):
        agent_id = a
        agent_ip = b
        job_info = agent_heartbeat(a, b)

        #complete mock scan and upload(processes & accounts only)
        scan_task_id = job_info['scanId']
        job_authenticator = job_info['authenticator']
        progress_url =  "/api/agents/progress"

        #first set of headers to update status of scan task
        check_heads1 = copy.deepcopy(base.base_headers)
        check_heads1['scanid'] = scan_task_id
        check_heads1['authenticator'] = job_authenticator
        check_heads1['replytype'] = "completed"
        # headers for all subsequent progress heartbeats after inital progress 
        check_heads2 = copy.deepcopy(base.base_headers)
        check_heads2['authorization'] = 'agent ' + agent_id
        check_heads2['scanid'] = scan_task_id
        check_heads2['authenticator'] = job_authenticator

        check_body = {}
        check_body['elapsed'] = 69
        #post request to /survey/reply , headers: scanid, authenticator, replytype, body:{"elapsed":1}
        response = base.request_post(progress_url, request_headers=check_heads1, request_body=check_body)
        resp_stat = response.status_code
        print(resp_stat)
        x = 0
        while resp_stat != 204 and x <= 10:
            response = base.request_post(progress_url, request_headers=check_heads2, request_body=check_body)
            resp_stat = resp_stat
            print(resp_stat)
            time.sleep(14)
            x += 1
            if x == 10 and resp_stat != 204:
                raise Exception("Failed!, job not ready for upload")

        #get list of upload urls for item types in scan
        upload_urls = []
        filename_manifest = []
        survey_payload_items = ['process', 'account']
        #item_type_count = 1 #number of items like processes, accounts etc, +1 for manifest.json

        upload_url_headers = copy.deepcopy(base.base_headers)
        upload_url_headers['authenticator'] = job_authenticator
        upload_url_headers['scanId'] = scan_task_id
        upload_url_headers['Authorization'] = f"agent {agent_id}"

        """
        upload url POST request sent to server for each piece of the survey upload
        with the expected file name included in the headers. Filename is then added to list
        which will be included in manifest.json upload.
        """
        get_upload_url = "/api/agents/uploadUrl"
        #expecting dict of items to be included in scan payload ["process", "autostart", etc.] 
        item_type = survey_payload_items
        item_type_count = len(item_type)
        x = 0
        while x <= item_type_count:
            if x == item_type_count:
                upload_url_headers['filename'] = "manifest.json.gz"
                print("manifest.json")
            else:
                filename = str(item_type[x]) + "-0000.ndjson.gz"
                print(filename)
                upload_url_headers['filename'] = filename
                filename_manifest.append(filename)
            url_response = base.request_get(get_upload_url, request_headers=upload_url_headers)
            print(f"upload url headers {upload_url_headers}")
            url_text = eval(url_response.text)
            upload_urls.append(url_text[0])
            x += 1

        x = 0
        while x < len(upload_urls):
            headers = copy.deepcopy(base.base_headers)
            headers['authenticator'] = job_authenticator

            if x == len(upload_urls) - 1:
                # manifest json generation is last piece of survey upload to be generated nd pushed to the server
                headers['filename'] = "manifest.json.gz"
                manifest_data = {
                                "files": filename_manifest,
                                "hostInfo":{
                                    "architecture": "64-bit",
                                    "cpe23Uri": None,
                                    "domain": "fake.int",
                                    "hostname": "fakehost.int",
                                    "ip": str(agent_ip),
                                    "agentId": str(agent_id),
                                    "osVersion": "Windows 5000"
                                },
                                "surveyInfo":{
                                    "authenticator": str(job_authenticator),
                                    "endTime": current_timestamp,
                                    "outputFileName": None,
                                    "postback": None,
                                    "scanId": str(scan_task_id),
                                    "startTime": current_timestamp,
                                    "surveyVersion": "1.0.123",
                                    "totalTasks": 0
                                }
                            }
                b = json.dumps(manifest_data)
                c = bytearray(b, 'utf8')
                gzip_survey = gzip.compress(c)
                print("survey manifest data created")
                                
            else:
                headers['filename'] = filename_manifest[x]
                payload_name = item_type[x]
                if payload_name == "process":
                    gzip_survey = open(process_payload, "rb")
                elif payload_name == "account":
                    gzip_survey = open(account_payload, "rb")
                else:
                    raise Exception("Invalid payload name specified")

                print(f"survey file {filename_manifest[x]} created")

            upload_response = requests.put(upload_urls[x], data=gzip_survey)
            print(upload_response.request.headers)
            print(upload_response.text)
            print(f"{upload_response.status_code}")

            #complete survey upload workflow with post to /uploadCompleted. This request lest the server know the upload is done for this particular pieces of the payload, scan will time out if this is not sent
            upload_fin_url = "/api/agents/uploadCompleted"
            upload_fin_response = base.request_post(upload_fin_url, request_headers=headers)
            print(f"{upload_fin_response.status_code}")
            #print(f"{response1.json()}")
            #print(f"file upload completed. HTTP status: {response.status_code}")
            x += 1


if __name__=="__main__":

    for x in range(50):
        p1 = Process(target=register_agent())
        p1.start()
        p1.join()

    print(f"{len(agent_ids)} agents registered, waiting 70 for memcache before proceeding")
    time.sleep(70)

    p2 = Process(target=mock_rts())
    p2.start()
    p2.join()


print(f"Done!")
