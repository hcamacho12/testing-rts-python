#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""discover tab interactions

"""

from infocyte import controller, target, schedule
import random

cnt = controller.ControllerGroups()
tgt = target.Target()
sch = schedule.Schedule()

class DiscoverTab(object):
    def __init__(self):
        pass

    def monitored_target(self):
        """create new target group

        target group created with default controller group

        Parameters:
            - None
        """
        #collect controller group info
        controller_group_request = cnt.get_controller_group_by_field("name", "Controller Group 1")
        controller_group_info = controller_group_request.json()
        controller_group_id = controller_group_info[0]['id']
        print(f"Controller group 1 id: {controller_group_id}")

        #target group creation
        target_create_response = tgt.new_target(f"new{random.randint(0, 999)}", controller_group_id)

        if target_create_response.status_code == 200:
            target_info = target_create_response.json()
            target_id = target_info['id']
            #setting target group to monitored status
            sch.continuous_monitoring(target_id)

            return [target_info, target_id, controller_group_id]

        else:
            raise Exception(f"Unexpected status code {target_create_response.status_code}")