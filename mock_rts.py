#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Mock rts loading test


"""

from infocyte import hunt_base
from common import agent_mocks, discover_tab
import time
import copy
import json
import requests
import gzip
import itertools

base = hunt_base.BaseRequests()
a_mocks = agent_mocks.HuntAgent()
disc_tab = discover_tab.DiscoverTab()

ts = time.gmtime()
current_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", ts)

#set url and token values here
#os.environ['HUNT_URL'] = "https://testhomer19.infocyte.com"
#os.environ['HUNT_TOKEN'] = "api token"

#number of agents
agent_count = 1
#number of process ndjson payloads per mock rts upload
proc_payload_count = 1
# agent memcache sleep. how long to wait(s) before proceeding with rts scans after agent registration and approval
agt_mem = 70

#survey payload files stored locally, can be generated using offline scan
process_payload = "/home/homer/Downloads/HostSurvey/process-0000.ndjson.gz"
account_payload = "/home/homer/Downloads/HostSurvey/account-0000.ndjson.gz"
memscan_payload_path = "" #todo
av_payload_path = "" #todo

def mock_rts():

    for (a, b) in itertools.zip_longest(agent_data[0], agent_data[1]):
        #upload_urls.clear()
        agent_id = a
        agent_ip = b
        job_info = a_mocks.agent_heartbeat(a, b)

        scan_data = a_mocks.progress_scan(job_info, agent_id)
        job_authenticator = scan_data[0]
        scan_task_id = scan_data[1]

        #get list of upload urls for item types in scan
        upload_urls = []
        filename_manifest = []
        survey_payload_items = ['process', 'account']

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
        # how many upload urls?
        item_type = survey_payload_items
        item_type_count = len(item_type)

        x = 0
        while x <= item_type_count:
            if x == item_type_count:
                filename = "manifest.json.gz"
                upload_url_headers['filename'] = filename
                upload_url = a_mocks.fetch_upload_url(filename, upload_url_headers)
                upload_urls.append(upload_url)
            else:
                if item_type[x] == "process":
                    y = 0
                    while y <= proc_payload_count:#range of process ndjson files to upload
                        filename =f"{item_type[0]}-000{y}.ndjson.gz"
                        filename_manifest.append(filename)
                        upload_url = a_mocks.fetch_upload_url(filename, upload_url_headers)
                        upload_urls.append(upload_url)
                        y += 1
                else:
                    filename =f"{item_type[x]}-0000.ndjson.gz"
                    filename_manifest.append(filename)
                    upload_url = a_mocks.fetch_upload_url(filename, upload_url_headers)
                    upload_urls.append(upload_url)

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
                                    "hostname": "fakeh'ost'.int",
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
                if 'process' in filename_manifest[x]:
                    gzip_survey = open(process_payload, "rb")
                elif 'account' in filename_manifest[x]:
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

    #create single target group to assign agents to
    target_data = disc_tab.monitored_target()

    #register agents iterating over count specified in agent_count variable
    # returns array of arrays agent_ids, agent_ips
    for x in range(agent_count):
        agent_data = a_mocks.register_agent(target_data)

    print(f"{agent_count} agents registered, waiting {agt_mem} seconds for memcache before proceeding")
    time.sleep(agt_mem)

    mock_rts()

print(f"Done!")
