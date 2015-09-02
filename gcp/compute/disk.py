# #######
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
from cloudify import ctx
from cloudify.decorators import operation

from gcp.compute import utils
from gcp.compute import constants
from gcp.gcp import GoogleCloudPlatform
from gcp.gcp import check_response


class Disk(GoogleCloudPlatform):
    def __init__(self,
                 config,
                 logger,
                 name,
                 image=None,
                 size_gb=None):
        super(Disk, self).__init__(config, logger, name)
        self.image = image
        self.sizeGb = size_gb

    def to_dict(self):
        body = {
            'description': 'Cloudify generated disk',
            'name': self.name
        }
        if self.image:
            body['sourceImage'] = self.image
        if self.sizeGb:
            body['sizeGb'] = self.sizeGb
        return body

    def disk_to_insert_instance_dict(self, mount_name):
        disk_info = self.get()
        body = {
            'deviceName': mount_name,
            'boot': False,
            'mode': 'READ_WRITE',
            'autoDelete': False,
            'source': disk_info['selfLink']
        }
        return body

    @check_response
    def get(self):
        return self.discovery.disks().get(
            project=self.project,
            zone=self.zone,
            disk=self.name).execute()

    @check_response
    def create(self):
        return self.discovery.disks().insert(
            project=self.project,
            zone=self.zone,
            body=self.to_dict()).execute()

    @check_response
    def delete(self):
        return self.discovery.disks().delete(
            project=self.project,
            zone=self.zone,
            disk=self.name).execute()


@operation
@utils.throw_cloudify_exceptions
def create(image, name, size, **kwargs):
    name = get_disk_name(name)
    gcp_config = utils.get_gcp_config()
    disk = Disk(gcp_config,
                ctx.logger,
                image=image,
                name=name,
                size_gb=size)
    create_disk(disk)
    ctx.instance.runtime_properties[constants.NAME] = name
    ctx.instance.runtime_properties[constants.DISK] = \
        disk.disk_to_insert_instance_dict(name)


def get_disk_name(name):
    if utils.should_use_external_resource():
        return utils.assure_resource_id_correct()
    else:
        return name or utils.get_gcp_resource_name(ctx.instance.id)


@utils.create_resource
def create_disk(disk):
    disk.create()


@operation
@utils.retry_on_failure('Retrying deleting disk')
@utils.throw_cloudify_exceptions
def delete(**kwargs):
    gcp_config = utils.get_gcp_config()
    name = ctx.instance.runtime_properties.get(constants.NAME, None)
    disk = Disk(gcp_config,
                ctx.logger,
                name=name)
    delete_disk(disk)
    ctx.instance.runtime_properties.pop(constants.DISK, None)
    ctx.instance.runtime_properties.pop(constants.NAME, None)


def delete_disk(disk):
    if not utils.should_use_external_resource():
        disk.delete()


@operation
@utils.throw_cloudify_exceptions
def add_boot_disk(**kwargs):
    disk_body = ctx.target.instance.runtime_properties[constants.DISK]
    disk_body['boot'] = True
    ctx.source.instance.runtime_properties[constants.DISK] = disk_body