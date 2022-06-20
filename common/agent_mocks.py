#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""mock agent interactions

"""

from infocyte import hunt_base, agent
import random
import time
import uuid
import copy
import requests
import json

base = hunt_base.BaseRequests()
agt = agent.Agent()

agent_ids = []
agent_ips = []
filename_manifest = []

class HuntAgent(object):
    def __init_(self):
        pass

    def assign_agent_tg(self, agent_id, target_id):
        """assign agent to target group

        Parameters:
            - agent_id: agent id to be assigned to target group
            - target_id: target group id to assign agent to
        """
        #assign agent to tg
        tg_assign_response = agt.assign_agent_tg(agent_id, target_id)
        if tg_assign_response.status_code == 200:
            print(f"Agent {agent_id} assigned to target group {target_id}")
        else:
            raise Exception(f"Unexpected response status {tg_assign_response.status_code}")

    def register_agent(self, target_info):
        """register mock agent

        Parameters:
            - target_info: json response from new target group creation request
        """
        #passing target group info into variable instead of creating a new tg each time
        target_data = target_info
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
        time.sleep(random.randint(0, 1))
        if register_response.status_code == 200:
            #resp_agent_id = agent_id
            #print(f"agent with id: {agent_id} created")
            response = agt.approve_agent(agent_id)
            self.assign_agent_tg(agent_id, target_data[1])

            return [agent_ids, agent_ips]  
        else:
            raise Exception(f"agent register failure {register_response.status_code}\nresponse body {register_response.json()}")

    def agent_heartbeat(self, agent_id, agent_ip):
        """ mock agent heartbeat request

        heartbeat request will also fetch a job for mock agent from the server queue if available.
        Job data returned in response json for heartbeat request.

        Parameters:
            - agent_id: agent id for heartbeat body
            - agent_ip: agent ip address for heartbeat body
        """
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

    def fetch_upload_url(self, filename, upload_url_headers):
        get_upload_url = "/api/agents/uploadUrl"
        filename_manifest.append(filename)
        print(filename)
        upload_url_headers['filename'] = filename

        url_response = base.request_get(get_upload_url, request_headers=upload_url_headers)
        #print(f"upload url headers {upload_url_headers}")
        url_text = eval(url_response.text)
        upload_url = url_text[0]

        return upload_url

    def custom_headers(self, headers={}):
        headers.update(copy.deepcopy(base.base_headers))
        return headers 
        


    def progress_scan(self, scan_job, agent_id):
        scan_task_id = scan_job['scanId']
        job_authenticator = scan_job['authenticator']

        progress_url =  "/api/agents/progress"

        job_headers = {"scanid":scan_task_id, "authenticator":job_authenticator}
        scan_headers = self.custom_headers(job_headers)

        #first set of headers to update status of scan task
        heads1 = {"scanid":scan_task_id, "authenticator":job_authenticator, "replytype":"completed"}
        check_heads1 = self.custom_headers(heads1)

        # headers for all subsequent progress heartbeats after inital progress 
        heads2 = {"scanid":scan_task_id, "authenticator":job_authenticator}
        check_heads2 = self.custom_headers(heads2)
        check_heads2['authorization'] = 'agent ' + agent_id

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

        return [job_authenticator, scan_task_id]
