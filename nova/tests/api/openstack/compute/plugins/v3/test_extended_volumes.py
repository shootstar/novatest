# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from lxml import etree
import webob

from nova.api.openstack.compute.plugins.v3 import extended_volumes
from nova import compute
from nova.objects import instance as instance_obj
from nova.openstack.common import jsonutils
from nova import test
from nova.tests.api.openstack import fakes

UUID1 = '00000000-0000-0000-0000-000000000001'
UUID2 = '00000000-0000-0000-0000-000000000002'
UUID3 = '00000000-0000-0000-0000-000000000003'


def fake_compute_get(*args, **kwargs):
    return fakes.stub_instance(1, uuid=UUID1)


def fake_compute_get_all(*args, **kwargs):
    db_list = [fakes.stub_instance(1), fakes.stub_instance(2)]
    fields = instance_obj.INSTANCE_DEFAULT_FIELDS
    return instance_obj._make_instance_list(args[1],
                                            instance_obj.InstanceList(),
                                            db_list, fields)


def fake_compute_get_instance_bdms(*args, **kwargs):
    return [{'volume_id': UUID1}, {'volume_id': UUID2}]


class ExtendedVolumesTest(test.TestCase):
    content_type = 'application/json'
    prefix = 'os-extended-volumes:'

    def setUp(self):
        super(ExtendedVolumesTest, self).setUp()
        self.Controller = extended_volumes.ExtendedVolumesController()
        fakes.stub_out_nw_api(self.stubs)
        self.stubs.Set(compute.api.API, 'get', fake_compute_get)
        self.stubs.Set(compute.api.API, 'get_all', fake_compute_get_all)
        self.stubs.Set(compute.api.API, 'get_instance_bdms',
                       fake_compute_get_instance_bdms)
        self.app = fakes.wsgi_app_v3(init_only=('os-extended-volumes',
                                                'servers'))

    def _make_request(self, url):
        req = webob.Request.blank(url)
        req.headers['Accept'] = self.content_type
        res = req.get_response(self.app)
        return res

    def _get_server(self, body):
        return jsonutils.loads(body).get('server')

    def _get_servers(self, body):
        return jsonutils.loads(body).get('servers')

    def test_show(self):
        url = '/v3/servers/%s' % UUID1
        res = self._make_request(url)

        self.assertEqual(res.status_int, 200)
        server = self._get_server(res.body)
        exp_volumes = [{'id': UUID1}, {'id': UUID2}]
        if self.content_type == 'application/json':
            actual = server.get('%svolumes_attached' % self.prefix)
        elif self.content_type == 'application/xml':
            actual = [dict(elem.items()) for elem in
                      server.findall('%svolume_attached' % self.prefix)]
        self.assertEqual(exp_volumes, actual)

    def test_detail(self):
        url = '/v3/servers/detail'
        res = self._make_request(url)

        self.assertEqual(res.status_int, 200)
        exp_volumes = [{'id': UUID1}, {'id': UUID2}]
        for i, server in enumerate(self._get_servers(res.body)):
            if self.content_type == 'application/json':
                actual = server.get('%svolumes_attached' % self.prefix)
            elif self.content_type == 'application/xml':
                actual = [dict(elem.items()) for elem in
                          server.findall('%svolume_attached' % self.prefix)]
            self.assertEqual(exp_volumes, actual)


class ExtendedVolumesXmlTest(ExtendedVolumesTest):
    content_type = 'application/xml'
    prefix = '{%s}' % extended_volumes.ExtendedVolumes.namespace

    def _get_server(self, body):
        return etree.XML(body)

    def _get_servers(self, body):
        return etree.XML(body).getchildren()
